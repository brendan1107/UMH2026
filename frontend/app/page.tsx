"use client";

import { useState } from "react";
import { signInWithEmailAndPassword, signOut } from "firebase/auth";
import { auth } from "@/lib/firebase";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [userEmail, setUserEmail] = useState<string | null>(null);
    const [token, setToken] = useState<string | null>(null);

    const handleLogin = async () => {
        try {
            const res = await signInWithEmailAndPassword(auth, email, password);
            const user = res.user;

            setUserEmail(user.email);

            const idToken = await user.getIdToken();
            setToken(idToken);

            console.log("LOGIN SUCCESS:", user);
            console.log("TOKEN:", idToken);
        } catch (err: any) {
            console.error("LOGIN ERROR:", err.message);
            alert(err.message);
        }
    };

    const handleLogout = async () => {
        await signOut(auth);
        setUserEmail(null);
        setToken(null);
    };

    return (
        <div style={{ padding: "20px", fontFamily: "Arial" }}>
            <h1>🔥 Firebase Login Test</h1>

            {!userEmail ? (
                <>
                    <input
                        placeholder="Email"
                        onChange={(e) => setEmail(e.target.value)}
                        style={{ display: "block", marginBottom: "10px" }}
                    />

                    <input
                        type="password"
                        placeholder="Password"
                        onChange={(e) => setPassword(e.target.value)}
                        style={{ display: "block", marginBottom: "10px" }}
                    />

                    <button onClick={handleLogin}>Login</button>
                </>
            ) : (
                <>
                    <h2>✅ Logged in as:</h2>
                    <p>{userEmail}</p>

                    <button onClick={handleLogout}>Logout</button>

                    <h3 style={{ marginTop: "20px" }}>🔑 Firebase Token:</h3>
                    <textarea
                        value={token || ""}
                        readOnly
                        rows={6}
                        style={{ width: "100%" }}
                    />
                </>
            )}
        </div>
    );
}