import Link from "next/link";
import { Icon } from "../components/icons";

export default function NotFound() {
  return (
    <div className="page">
      <section className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
        <p style={{ fontSize: 48 }} aria-hidden="true">
          🧭
        </p>
        <h1 style={{ fontSize: 26, margin: "10px 0 8px" }}>Bu sayfayı bulamadık</h1>
        <p className="muted-text" style={{ maxWidth: 520, margin: "0 auto 20px" }}>
          Adres değişmiş olabilir. Kaybolmak sorun değil: koçun seni doğru adıma götürmesi için
          aşağıdaki bağlantılardan devam et.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link className="btn btn-primary" href="/">
            Ana sayfaya dön <Icon name="arrow" size={18} />
          </Link>
          <Link className="btn btn-soft" href="/calis">
            Çalışmaya devam et
          </Link>
        </div>
      </section>
    </div>
  );
}
