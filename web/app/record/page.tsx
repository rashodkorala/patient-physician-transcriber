import type { Metadata } from "next";
import RecordView from "@/components/RecordView";

export const metadata: Metadata = { title: "Record · Demo Night Interpreter" };

export default function RecordPage() {
  return <RecordView />;
}
