"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getSession } from "@/lib/auth/session";
import { LoadingState } from "@/components/ui/states";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getSession() ? "/command" : "/login");
  }, [router]);
  return (
    <main className="flex h-screen items-center justify-center">
      <LoadingState label="INITIALIZING VAYNEX" />
    </main>
  );
}
