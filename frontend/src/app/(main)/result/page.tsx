import { redirect } from "next/navigation";

export default function ResultLandingPage() {
  // If someone lands on /result without an ID, just send them home
  redirect("/");
}
