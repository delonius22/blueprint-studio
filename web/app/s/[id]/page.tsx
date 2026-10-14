"use client";

import { useParams } from "next/navigation";
import { Workspace } from "../../../components/Workspace";

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  return <Workspace sessionId={id} />;
}
