"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, UserOut } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";

/**
 * Shared auth guard for every authenticated page: redirects to /login if
 * there's no valid session, otherwise resolves the current user + token.
 */
export function useRequireAuth() {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = getToken();
    if (!t) {
      router.push("/login");
      return;
    }
    api
      .me(t)
      .then((u) => {
        setUser(u);
        setToken(t);
      })
      .catch(() => {
        clearToken();
        router.push("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  return { user, token, loading };
}
