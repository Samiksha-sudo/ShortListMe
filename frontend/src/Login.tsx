import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { login, type AuthResult } from "./api";
import AuthLayout from "./AuthLayout";
import Field from "./ui/Field";
import { Button, ErrorState } from "./ui/primitives";

export default function Login({ onDone, onSwitch, onForgot }: {
  onDone: (r: AuthResult) => void;
  onSwitch: () => void;
  onForgot: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState(false);
  const mutation = useMutation({ mutationFn: () => login(email.trim(), password), onSuccess: onDone });

  const emailMissing = !email.trim();
  const passwordMissing = !password;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!emailMissing && !passwordMissing) mutation.mutate();
  };

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to keep tailoring your CV.">
      <form onSubmit={submit} noValidate>
        {mutation.isError && <div style={{ marginBottom: 16 }}><ErrorState title="Couldn't log you in" message={mutation.error.message} /></div>}

        <Field label="Email" type="email" autoComplete="email" placeholder="you@example.com" value={email}
          onChange={(e) => setEmail(e.target.value)} error={touched && emailMissing ? "Enter your email address." : undefined} />
        <Field label="Password" type="password" autoComplete="current-password" placeholder="Your password" value={password}
          onChange={(e) => setPassword(e.target.value)} error={touched && passwordMissing ? "Enter your password." : undefined} />

        <div className="auth-row">
          <span />
          <button type="button" className="link-btn" onClick={onForgot}>Forgot password?</button>
        </div>

        <Button type="submit" variant="primary" size="lg" block loading={mutation.isPending}>
          {mutation.isPending ? "Logging in…" : "Log in"}
        </Button>
      </form>
      <p className="auth-foot">New here? <button type="button" className="link-btn" onClick={onSwitch}>Create an account</button></p>
    </AuthLayout>
  );
}
