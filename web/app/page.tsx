"use client";

import { CopilotChat, CopilotKit } from "@copilotkit/react-core/v2";
import { AGENT_NAME, RUNTIME_PATH } from "../lib/constants";
import styles from "./page.module.css";

export default function Home() {
  return (
    <CopilotKit runtimeUrl={RUNTIME_PATH} agentId={AGENT_NAME}>
      <div className={styles.shell}>
        <header className={styles.header}>
          <h1>Blueprint Studio</h1>
        </header>
        <main className={styles.chat}>
          <CopilotChat agentId={AGENT_NAME} />
        </main>
      </div>
    </CopilotKit>
  );
}
