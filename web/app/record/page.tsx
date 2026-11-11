import type { Metadata } from "next";
import RecordView from "@/components/RecordView";

export const metadata: Metadata = { title: "Record, Medical interpreter" };

export default function RecordPage() {
  return <RecordView />;
}
