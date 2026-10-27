"use client";

import { useRouter } from "next/navigation";
import { SessionList } from "../components/sessions/SessionList";
import styles from "./page.module.css";

export default function Home() {
  const router = useRouter();
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Blueprint Studio</h1>
      </header>
      <main className={styles.main}>
        <SessionList onOpen={(id) => router.push(`/s/${id}`)} />
      </main>
    </div>
  );
}
