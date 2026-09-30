import type { Metadata } from "next";
import { StudyFlow } from "../../components/study-flow";

export const metadata: Metadata = {
  title: "Çalışma alanı",
  description:
    "Günün sorularını çöz, yanlışını öz değerlendirmeyle anlat ve AI koçtan H1–H7 hata teşhisi al. Üslü ve kareköklü ifadelerden pekiştirme soruları.",
  alternates: { canonical: "/calis" },
};

export default function CalisPage() {
  return (
    <div className="page">
      <section className="study-hero">
        <div>
          <span className="eyebrow">Bugünün çalışması</span>
          <h1>Matematik · Üslü İfadeler</h1>
          <p>
            10 soru · seviye 2 · hata analizi dâhil. Yanlış yaptığında koç doğrudan &ldquo;konu
            eksiğin var&rdquo; demez; önce ilk hata noktasını birlikte bulur.
          </p>
        </div>
        <a className="btn btn-primary" href="#sorular">
          Soruya geç
        </a>
      </section>

      <div className="study-stats">
        <div>
          <small>Bugünün hedefi</small>
          <b>10 soru</b>
          <span className="delta">4 soru tamamlandı</span>
        </div>
        <div>
          <small>Odak kazanım</small>
          <b>H3 · Okuma</b>
          <span className="muted-text">Bilgiyi problem içinde yorumlama</span>
        </div>
        <div>
          <small>Kazanç</small>
          <b>+10 XP</b>
          <span className="delta">Hata analizi yaparsan +5 XP</span>
        </div>
      </div>

      <section id="sorular" aria-label="Soru akışı">
        <StudyFlow />
      </section>

      <section className="card" aria-labelledby="nasil-calisir">
        <h2 id="nasil-calisir">Şimdi ne yapmalıyım?</h2>
        <p className="coach-note" style={{ marginTop: 12 }}>
          Önce soruyu kendi başına çöz. Yanlış yaparsan hangi noktada takıldığını seç, istersen
          çözüm fotoğrafını ekle. Koç; <strong>H1</strong> kavram, <strong>H2</strong> yöntem,{" "}
          <strong>H3</strong> okuma/modelleme, <strong>H4</strong> işlem, <strong>H5</strong>{" "}
          gereksiz bilgi, <strong>H6</strong> ilişkilendirme ve <strong>H7</strong> dikkat
          kodlarından uygun olanı seçip kısa bir tekrar planı verir.
        </p>
        <p className="muted-text" style={{ marginTop: 10, fontSize: 12.5 }}>
          Eklediğin ses, açıklama ve fotoğraflar yalnızca analiz için kullanılır; analiz tamamlandığında
          kalıcı olarak silinir ve puanlama amacıyla saklanmaz.
        </p>
      </section>
    </div>
  );
}
