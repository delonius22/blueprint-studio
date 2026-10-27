"use client";

import { useRouter } from "next/navigation";
import { NewSessionForm } from "../components/sessions/NewSessionForm";
import { SessionList } from "../components/sessions/SessionList";
import { ThemeSwitcher } from "../components/theme/ThemeSwitcher";
import styles from "./page.module.css";

export default function Home() {
  const router = useRouter();
  return (
    <div className={styles.page}>
      <header className={`panel ${styles.header}`}>
        <h1>Blueprint Studio</h1>
        <ThemeSwitcher />
      </header>
      <main className={styles.main}>
        <div className={styles.start}>
          <NewSessionForm onOpen={(id) => router.push(`/s/${id}`)} />
        </div>
        <div className={styles.sessions}>
          <SessionList />
        </div>
      </main>
    </div>
  );
}
