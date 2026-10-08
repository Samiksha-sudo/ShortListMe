import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { signup, type AuthResult } from "./api";
import AuthLayout from "./AuthLayout";
import Field from "./ui/Field";
import { Button, ErrorState } from "./ui/primitives";

const MIN_PASSWORD = 8;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function SignUp({ onDone, onSwitch }: {
  onDone: (r: AuthResult) => void;
  onSwitch: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState(false);
  const mutation = useMutation({ mutationFn: () => signup(email.trim(), password), onSuccess: onDone });

  const emailError = EMAIL_RE.test(email.trim()) ? "" : "Enter a valid email address.";
  const passwordError = password.length >= MIN_PASSWORD ? "" : `Use at least ${MIN_PASSWORD} characters.`;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!emailError && !passwordError) mutation.mutate();
  };

  return (
    <AuthLayout title="Create your account" subtitle="Start tailoring your CV to the roles you want.">
      <form onSubmit={submit} noValidate>
        {mutation.isError && <div style={{ marginBottom: 16 }}><ErrorState title="Couldn't create your account" message={mutation.error.message} /></div>}

        <Field label="Email" type="email" autoComplete="email" placeholder="you@example.com" value={email}
          onChange={(e) => setEmail(e.target.value)} hint="Use an address you check often."
          error={touched ? emailError || undefined : undefined} />
        <Field label="Password" type="password" autoComplete="new-password" placeholder="At least 8 characters" value={password}
          onChange={(e) => setPassword(e.target.value)} hint={`Minimum ${MIN_PASSWORD} characters.`}
          error={touched ? passwordError || undefined : undefined} />

        <Button type="submit" variant="primary" size="lg" block loading={mutation.isPending}>
          {mutation.isPending ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="auth-foot">Already have an account? <button type="button" className="link-btn" onClick={onSwitch}>Log in</button></p>
    </AuthLayout>
  );
}
