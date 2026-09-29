"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as authService from "@/services/auth";
import { onSessionEnd, type SessionEndReason } from "@/stores/session";
import type { LoginPayload, RegisterPayload, User } from "@/types/api";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  /** Why the last session ended, so the login page can explain it. */
  endReason: SessionEndReason | null;
  login: (payload: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  /** Replace the cached user after a successful /users/me update. */
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Tells other open tabs to drop their in-memory session when this tab signs out.
const CHANNEL_NAME = "job-agent:auth";

function openChannel(): BroadcastChannel | null {
  return typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel(CHANNEL_NAME);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUserState] = useState<User | null>(null);
  const [endReason, setEndReason] = useState<SessionEndReason | null>(null);

  const becomeAnonymous = useCallback(
    (reason: SessionEndReason | null) => {
      setUserState(null);
      setStatus("anonymous");
      setEndReason(reason);
      queryClient.clear();
    },
    [queryClient],
  );

  // Restore the session from the refresh cookie on first load. refreshSession() is
  // single-flight, so React StrictMode's double effect doesn't rotate the token twice.
  useEffect(() => {
    let cancelled = false;
    authService
      .restoreSession()
      .then((restored) => {
        if (cancelled) return;
        setUserState(restored);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!cancelled) becomeAnonymous(null);
      });
    return () => {
      cancelled = true;
    };
  }, [becomeAnonymous]);

  useEffect(() => onSessionEnd((reason) => becomeAnonymous(reason)), [becomeAnonymous]);

  useEffect(() => {
    const channel = openChannel();
    if (!channel) return;
    channel.onmessage = (event: MessageEvent<{ type?: string }>) => {
      if (event.data?.type === "signed_out") becomeAnonymous("signed_out");
    };
    return () => channel.close();
  }, [becomeAnonymous]);

  const signIn = useCallback((signedIn: User) => {
    setUserState(signedIn);
    setStatus("authenticated");
    setEndReason(null);
    return signedIn;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      endReason,
      login: async (payload) => signIn(await authService.login(payload)),
      register: async (payload) => signIn(await authService.register(payload)),
      logout: async () => {
        await authService.logout();
        const channel = openChannel();
        channel?.postMessage({ type: "signed_out" });
        channel?.close();
      },
      setUser: setUserState,
    }),
    [status, user, endReason, signIn],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** For components that only render once signed in. */
export function useCurrentUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("useCurrentUser requires an authenticated session");
  return user;
}
