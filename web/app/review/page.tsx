import type { Metadata } from "next";
import ReviewScreen from "@/components/ReviewScreen";

export const metadata: Metadata = { title: "Your visit · Demo Night Interpreter" };

export default function ReviewPage() {
  return <ReviewScreen />;
}
