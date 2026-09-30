"use client";

import { Suspense } from "react";
import { LoadingState } from "@/components/ui/states";
import { SimulationCenter } from "@/components/simulation/simulation-center";

export default function SimulationPage() {
  return (
    <Suspense fallback={<LoadingState label="LOADING SIMULATION CENTER" />}>
      <SimulationCenter />
    </Suspense>
  );
}
