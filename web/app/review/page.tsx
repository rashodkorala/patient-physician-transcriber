import { redirect } from "next/navigation";

/** The patient's device moved to /patient (MDD-005, CDR-008); the old route still reaches it. */
export default function ReviewPage() {
  redirect("/patient");
}
