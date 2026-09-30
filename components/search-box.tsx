"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon } from "./icons";
import { errorTypes, resources, subjects, tasks } from "../data/content";

type Hit = {
  title: string;
  detail: string;
  href: string;
  external?: boolean;
};

/** Türkçe karakterleri sadeleştirerek arama yapmayı kolaylaştırır. */
function normalize(value: string) {
  return value
    .toLocaleLowerCase("tr")
    .replaceAll("ı", "i")
    .replaceAll("ş", "s")
    .replaceAll("ğ", "g")
    .replaceAll("ü", "u")
    .replaceAll("ö", "o")
    .replaceAll("ç", "c")
    .replace(/\s+/g, " ")
    .trim();
}

const index: Hit[] = [
  ...subjects.flatMap((subject) => [
    {
      title: subject.name,
      detail: `Ders · başarı %${subject.score}`,
      href: `/dersler#${subject.slug}`,
    },
    ...subject.topics.map((topic) => ({
      title: topic,
      detail: `${subject.name} konusu`,
      href: `/dersler#${subject.slug}`,
    })),
  ]),
  ...tasks.map((task) => ({ title: task.title, detail: task.detail, href: task.href })),
  ...resources.map((resource) => ({
    title: resource.title,
    detail: resource.detail.slice(0, 70) + "…",
    href: resource.href,
    external: resource.external,
  })),
  ...errorTypes.map((error) => ({
    title: `${error.code} · ${error.name}`,
    detail: error.definition,
    href: "/ilerleme",
  })),
];

export function SearchBox({ initialQuery = "" }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setQuery("");
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    function onDocumentClick(event: MouseEvent) {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, []);

  const hits = useMemo(() => {
    const q = normalize(query);
    if (q.length < 2) return [];
    return index
      .filter((hit) => normalize(hit.title).includes(q) || normalize(hit.detail).includes(q))
      .slice(0, 6);
  }, [query]);

  const showList = open && hits.length > 0;

  return (
    <div className="search" ref={boxRef}>
      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault();
          const first = hits[0];
          if (!first) return;
          setOpen(false);
          if (first.external) window.open(first.href, "_blank", "noopener");
          else router.push(first.href);
        }}
      >
        <Icon name="compass" size={18} className="search-ico" label={undefined} />
        <label className="sr-only" htmlFor="site-search">
          Konu, soru veya kaynak ara
        </label>
        <input
          id="site-search"
          type="search"
          value={query}
          placeholder="Konu, soru veya kaynak ara..."
          autoComplete="off"
          aria-expanded={showList}
          aria-controls="site-search-results"
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Escape") setOpen(false);
          }}
        />
      </form>

      {showList && (
        <ul className="search-results" id="site-search-results">
          {hits.map((hit) => (
            <li key={`${hit.href}-${hit.title}`}>
              {hit.external ? (
                <a href={hit.href} target="_blank" rel="noopener noreferrer" onClick={() => setOpen(false)}>
                  <b>{hit.title}</b>
                  <small>{hit.detail}</small>
                </a>
              ) : (
                <Link href={hit.href} onClick={() => setOpen(false)}>
                  <b>{hit.title}</b>
                  <small>{hit.detail}</small>
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
