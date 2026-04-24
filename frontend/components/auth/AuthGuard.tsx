"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "../../lib/firebase";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (!user) {
        // Not logged in, redirect if trying to access protected routes
        if (pathname.startsWith("/dashboard") || pathname.startsWith("/case")) {
          router.push("/login");
        } else {
          setLoading(false);
        }
      } else {
        // Logged in
        if (pathname === "/login" || pathname === "/register" || pathname === "/") {
          router.push("/dashboard");
        } else {
          setLoading(false);
        }
      }
    });

    return () => unsubscribe();
  }, [pathname, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-slate-300 border-t-slate-900 animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
