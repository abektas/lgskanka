"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "./icons";
import { tasks } from "../data/content";

const STORAGE_KEY = "lgs-ai-coach-tasks";

/** Günün görev listesi: tamamlananlar tarayıcıda saklanır. */
export function TaskList() {
  const [done, setDone] = useState<string[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        if (Array.isArray(parsed)) setDone(parsed.filter((id): id is string => typeof id === "string"));
      }
    } catch {
      /* bozuk kayıt: boş listeyle devam */
    }
    setReady(true);
  }, []);

  function toggle(id: string) {
    setDone((previous) => {
      const next = previous.includes(id) ? previous.filter((item) => item !== id) : [...previous, id];
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* depolama kapalıysa yalnızca bellekte tut */
      }
      return next;
    });
  }

  const completed = ready ? done.length : 0;
  const percent = Math.round((completed / tasks.length) * 100);

  return (
    <>
      <p className="task-progress">
        <b>
          {completed}/{tasks.length}
        </b>{" "}
        görev tamamlandı
        <span className="bar" aria-hidden="true">
          <i style={{ width: `${percent}%` }} />
        </span>
      </p>

      <ul className="task-list">
        {tasks.map((task) => {
          const isDone = done.includes(task.id);
          return (
            <li className={`task-row${isDone ? " is-done" : ""}`} key={task.id}>
              <span className="task-ico" aria-hidden="true">
                {task.icon}
              </span>
              <div>
                <b>
                  <Link href={task.href}>{task.title}</Link>
                </b>
                <small>
                  {task.detail} · ~{task.minutes} dk
                  <span className="xp-inline">+{task.xp} XP</span>
                </small>
              </div>
              <div className="task-actions">
                <button
                  type="button"
                  className={`btn btn-sm ${isDone ? "btn-soft" : "btn-mint"}`}
                  aria-pressed={isDone}
                  onClick={() => toggle(task.id)}
                >
                  {isDone ? (
                    <>
                      <Icon name="check" size={15} /> Tamam
                    </>
                  ) : (
                    "Başla"
                  )}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}
