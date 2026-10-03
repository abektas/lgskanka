#!/usr/bin/env bash
# TASK-QBANK-001 — Question Bank v2 migration testleri.
#
# Gerçek PostgreSQL'e karşı çalışır. Gereksinim: çalışan bir postgres
# (ya da TEST_DATABASE_URL) ve psql. Test verisi tamamen geçicidir.
#
# Kullanım:
#   tests/db/run_question_bank_v2_tests.sh            # TEST_DATABASE_URL ile
#   bash tests/db/run_question_bank_v2_tests.sh --local-test-container
#
# Kapsam: migration uygulanabilirliği, idempotency, FK/UNIQUE/CHECK
# kısıtları, H1-H7 dışı değer reddi, self/duplicate relation reddi,
# curriculum katman ayrımı ve mevcut verinin etkilenmemesi.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTAINER="lgs-qb-test-v2"
PASS=0
FAIL=0

psql_run() { psql "$1" -v ON_ERROR_STOP=1 -q -tA -c "$2" 2>&1; }

# Bir ifadenin hata vermesini BEKLERİZ. Hata üretiyorsa test geçer.
expect_error() {
  local label="$1" sql="$2"
  local out
  out="$(db_psql -v ON_ERROR_STOP=1 -q -c "$sql" 2>&1)"
  if printf '%s' "$out" | grep -qi 'ERROR'; then
    PASS=$((PASS+1)); printf '  ok   %s reddedildi\n' "$label"
  else
    FAIL=$((FAIL+1)); printf '  FAIL %s REDDEDILMEDI\n' "$label"
  fi
}

expect_ok() {
  local label="$1" sql="$2"
  local out
  out="$(db_psql -v ON_ERROR_STOP=1 -q -c "$sql" 2>&1)"
  if printf '%s' "$out" | grep -qi 'ERROR'; then
    FAIL=$((FAIL+1)); printf '  FAIL %s: %s\n' "$label" "$(printf '%s' "$out" | head -1)"
  else
    PASS=$((PASS+1)); printf '  ok   %s\n' "$label"
  fi
}

# --- Ortam hazırlığı ------------------------------------------------------
USE_DOCKER=0
[[ "${1:-}" == "--local-test-container" ]] && USE_DOCKER=1

if [[ $USE_DOCKER -eq 1 ]]; then
  echo "==> Geçici postgres konteyneri hazırlanıyor"
  docker rm -f "$CONTAINER" >/dev/null 2>&1
  docker run -d --name "$CONTAINER" -e POSTGRES_PASSWORD=testpw \
    -e POSTGRES_DB=lgs_qb_v2_test postgres:16 >/dev/null || { echo "docker kurulamadı"; exit 1; }
  for _ in $(seq 1 30); do
    docker exec "$CONTAINER" pg_isready -U postgres >/dev/null 2>&1 && break
    sleep 1
  done
  DB=lgs_qb_v2_test
  # db_psql stdin KULLANMAZ (-c dogrudan SQL alir). `docker exec -i`
  # kullanmak burada hataydi: sonraki script satirlari stdin'den okunup
  # yutuluyor ve testlerin sessizce atlanmasina yol aciyordu.
  db_psql() { docker exec "$CONTAINER" psql -U postgres -d "$DB" "$@"; }
  # Dosya/metin stdin'den beslenir; `-f -` psql'e "stdin'den oku" der.
  db_file() { cat | docker exec -i "$CONTAINER" psql -U postgres -d "$DB" -f - "$@"; }
  trap 'docker rm -f "$CONTAINER" >/dev/null 2>&1' EXIT
else
  : "${TEST_DATABASE_URL:?TEST_DATABASE_URL gerekli veya --local-test-container kullanın}"
  export PGPASSWORD="${TEST_PGPASSWORD:-}"
  db_psql() { psql "$TEST_DATABASE_URL" "$@"; }
  db_file() { psql "$TEST_DATABASE_URL" "$@"; }
fi

echo "==> Migration 001 uygulanıyor"
db_file -v ON_ERROR_STOP=1 -q < "$ROOT/db/001_question_bank.sql" || { echo "001 BAŞARISIZ"; exit 1; }
echo "==> Migration 002 uygulanıyor"
db_file -v ON_ERROR_STOP=1 -q < "$ROOT/db/002_question_bank_v2.sql" || { echo "002 BAŞARISIZ"; exit 1; }

echo "==> 002 tekrar uygulanıyor (idempotency)"
db_file -v ON_ERROR_STOP=1 -q < "$ROOT/db/002_question_bank_v2.sql" 2>/dev/null \
  && { PASS=$((PASS+1)); echo "  ok   idempotent"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL idempotency"; }

n=$(db_psql -tAc "select count(*) from pg_tables where schemaname='public'")
# 17 = 001'den gelen 2 (question_sources, questions) + 002'nin 15'i.
[[ "$n" == "17" ]] && { PASS=$((PASS+1)); echo "  ok   17 tablo (001:2 + 002:15)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL tablo sayısı: $n"; }

echo "==> Test verisi"
db_file -v ON_ERROR_STOP=1 -q <<'SQL'
insert into question_sources (id, source_type, official_index_url)
  values ('MEB-TEST-2024','REAL_LGS','https://odsgm.meb.gov.tr/test');
insert into subjects (id,name) values ('MAT','Matematik');
insert into units (id,layer_code,subject_id,name)
  values ('U1','LGS_REFERENCE_2018_PLUS','MAT','Sayılar');
insert into topics (id,unit_id,name)
  values ('T1','U1','Üslü İfadeler'),('T2','U1','Kareler');
insert into learning_outcomes (id,topic_id,statement) values ('LO1','T1','Üsleri karşılaştırır');
insert into skills (id,layer_code,name)
  values ('SK1','LGS_REFERENCE_2018_PLUS','Üslü ifadeyi yorumlar');
insert into questions (id,source_id,source_type,year,subject,grade,question_number,stem,options,status)
  values ('Q1','MEB-TEST-2024','REAL_LGS',2024,'MATEMATİK',8,1,'s','{"A":"1"}'::jsonb,'NEEDS_REVIEW'),
         ('Q2','MEB-TEST-2024','REAL_LGS',2024,'MATEMATİK',8,2,'s2','{"A":"2"}'::jsonb,'NEEDS_REVIEW');
insert into error_types values
 ('H1','Kavram eksikliği','kavram'),('H2','Yöntem / strateji','yöntem/strateji'),
 ('H3','Okuma / modelleme','okuduğunu anlama/modelleme'),('H4','İşlem hatası','işlem'),
 ('H5','Gereksiz bilgi','gereksiz bilgiyi ayıklama'),('H6','İlişkilendirme','bilgileri ilişkilendirme'),
 ('H7','Dikkat','dikkat');
SQL

echo "==> 1. Migration 001 verisi etkilenmemiş"
v=$(db_psql -tAc "select count(*) from questions")
[[ "$v" == "2" ]] && { PASS=$((PASS+1)); echo "  ok   mevcut sorular korundu"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL soru sayısı: $v"; }

echo "==> 2. Invalid H1-H7 reddi"
expect_error "H9 error type" "insert into question_pedagogy (question_id, primary_error_type) values ('Q1','H9');"
echo "==> 3. Invalid difficulty reddi"
expect_error "overall=1.5" "insert into question_difficulty (question_id, overall) values ('Q1', 1.5);"
echo "==> 4. Invalid confidence reddi"
expect_error "confidence=1.4" "insert into question_topics (question_id,topic_id,confidence) values ('Q1','T1',1.4);"
echo "==> 5. Self relation reddi"
expect_error "Q1->Q1" "insert into question_relations (question_id,related_question_id,relation_type) values ('Q1','Q1','VARIATION');"
echo "==> 6. Invalid relation_type reddi"
expect_error "BOGUS" "insert into question_relations (question_id,related_question_id,relation_type) values ('Q1','Q2','BOGUS');"
echo "==> 7. Geçerli kayıtlar kabul edilir"
expect_ok "primary topic" "insert into question_topics (question_id,topic_id,is_primary) values ('Q1','T1',true);"
expect_ok "geçerli difficulty" "insert into question_difficulty (question_id,overall,assessment_method,assessed_at) values ('Q1',0.6,'expert',now());"

echo "==> 8. Tek birincil kuralı"
expect_error "ikinci birincil topic" "insert into question_topics (question_id,topic_id,is_primary) values ('Q1','T2',true);"
expect_ok "is_primary=false serbest" "insert into question_topics (question_id,topic_id,is_primary) values ('Q1','T2',false);"

echo "==> 9. Duplicate relation reddi"
expect_ok "ilk SAME_CONCEPT" "insert into question_relations (question_id,related_question_id,relation_type) values ('Q1','Q2','SAME_CONCEPT');"
expect_error "ayni ilişki tekrar" "insert into question_relations (question_id,related_question_id,relation_type) values ('Q1','Q2','SAME_CONCEPT');"

echo "==> 10. İkincil hata birincil ile aynı olamaz"
expect_ok "pedagogy H1" "insert into question_pedagogy (question_id,primary_error_type,requires_reading) values ('Q1','H1',true);"
expect_error "ikincil=H1" "insert into question_secondary_error_types (question_id,error_type_code) values ('Q1','H1');"
expect_ok "ikincil=H3 farklı" "insert into question_secondary_error_types (question_id,error_type_code) values ('Q1','H3');"
expect_error "primary=H3 iken ikincil H3" \
  "update question_pedagogy set primary_error_type='H3' where question_id='Q1';"

echo "==> 11. FK bütünlüğü"
expect_error "olmayan soruya topic" "insert into question_topics (question_id,topic_id) values ('YOK','T1');"
expect_error "geçersiz katman" "insert into units (id,layer_code,subject_id,name) values ('U9','BOGUS','MAT','x');"

echo "==> 12. Curriculum katman ayrımı"
n=$(db_psql -tAc "select count(*) from curriculum_layers")
[[ "$n" == "2" ]] && { PASS=$((PASS+1)); echo "  ok   iki katman ayrı kayıt"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL katman sayısı: $n"; }
n=$(db_psql -tAc "select count(*) from units where layer_code='CURRENT_TYMM'")
[[ "$n" == "0" ]] && { PASS=$((PASS+1)); echo "  ok   katmanlar birleşmedi"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL katman birleşmesi"; }

echo "==> 13. Quality review tutarlılığı"
expect_error "reviewed_by var, reviewed_at yok" \
  "insert into question_quality (question_id,quality_status,reviewed_by) values ('Q2','APPROVED','ali');"
expect_ok "tutarlı review" \
  "insert into question_quality (question_id,quality_status,reviewed_by,reviewed_at) values ('Q2','APPROVED','ali',now());"

echo
echo "=============================="
echo " geçen: $PASS   kalan: $FAIL"
echo "=============================="
[[ $FAIL -eq 0 ]]
