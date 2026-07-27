"use client";

import { useCallback, useEffect, useState } from "react";
import { getArchive, getHealth, getProof } from "@/lib/api";
import type { Archive, Health, SubmissionProof } from "@/lib/types";

export function useArchive() {
  const [archive, setArchive] = useState<Archive | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [proof, setProof] = useState<SubmissionProof | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const archiveRequest = getArchive()
      .then((nextArchive) => {
        setArchive(nextArchive);
      })
      .catch((caught: unknown) => {
        setError(
          caught instanceof Error ? caught.message : "Archive unavailable.",
        );
      });
    const healthRequest = getHealth()
      .then((nextHealth) => {
        setHealth(nextHealth);
      })
      .catch((caught: unknown) => {
        setError(
          caught instanceof Error ? caught.message : "Archive unavailable.",
        );
      });
    const proofRequest = getProof()
      .then(setProof)
      .catch(() => setProof(null));
    await Promise.allSettled([archiveRequest, healthRequest, proofRequest]);
    setLoading(false);
  }, []);

  useEffect(() => {
    let active = true;
    let pending = 3;
    const finish = () => {
      pending -= 1;
      if (active && pending === 0) setLoading(false);
    };

    getArchive()
      .then((nextArchive) => {
        if (!active) return;
        setArchive(nextArchive);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Archive unavailable.",
        );
      })
      .finally(finish);

    getHealth()
      .then((nextHealth) => {
        if (!active) return;
        setHealth(nextHealth);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Archive unavailable.",
        );
      })
      .finally(finish);

    getProof()
      .then((nextProof) => {
        if (active) setProof(nextProof);
      })
      .catch(() => {
        if (active) setProof(null);
      })
      .finally(finish);

    return () => {
      active = false;
    };
  }, []);

  const ready =
    archive?.index_status === "ready" &&
    health?.videodb === "connected" &&
    health.archive_indexed;

  return { archive, health, proof, loading, error, ready, load };
}
