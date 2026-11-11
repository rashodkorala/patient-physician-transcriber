import type { Metadata } from "next";
import PatientScreen from "@/components/PatientScreen";

export const metadata: Metadata = { title: "Your visit" };

export default function PatientPage() {
  return <PatientScreen />;
}
