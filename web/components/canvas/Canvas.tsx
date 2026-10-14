// The design canvas (SPECS S11.2, S11.3): one panel per Design list, updated live.
import type { Design } from "../../lib/state";
import styles from "./Canvas.module.css";
import { Panel } from "./Panel";

function num(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(6)));
}

export function Canvas({ design }: { design: Design }) {
  return (
    <div className={styles.canvas}>
      <h2 className="visually-hidden">Design canvas</h2>
      <div className={styles.group}>
        <h3 className={styles.groupTitle}>Step 1 · Requirements</h3>
        <div className={styles.grid}>
          <Panel
            title="Functional requirements"
            items={design.functional_requirements.map((r) => ({ id: r.id, content: r.statement }))}
          />
          <Panel
            title="Non-functional requirements"
            items={design.non_functional_requirements.map((n) => ({
              id: n.id,
              content: (
                <>
                  <span className={styles.tag}>{n.category}</span> {n.statement}
                  {(n.metric || n.target != null || n.unit) && (
                    <div className={styles.detail}>
                      {[n.metric, n.target != null ? num(n.target) : null, n.unit]
                        .filter(Boolean)
                        .join(" ")}
                    </div>
                  )}
                </>
              ),
            }))}
          />
          <Panel
            title="Out of scope"
            items={design.out_of_scope.map((o) => ({ id: o.id, content: o.text }))}
          />
          <Panel
            title="Capacity estimates"
            items={design.capacity_estimates.map((e) => ({
              id: e.id,
              content: (
                <>
                  {e.quantity}
                  <div className={styles.detail}>
                    <code>{e.formula}</code> = {num(e.result)} {e.unit}
                  </div>
                </>
              ),
            }))}
          />
        </div>
      </div>
    </div>
  );
}
