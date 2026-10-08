import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { forgotPassword } from "./api";
import AuthLayout from "./AuthLayout";
import Field from "./ui/Field";
import { Alert, Button, ErrorState } from "./ui/primitives";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotPassword({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState(false);
  const mutation = useMutation({ mutationFn: () => forgotPassword(email.trim()) });

  const emailError = EMAIL_RE.test(email.trim()) ? "" : "Enter a valid email address.";

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!emailError) mutation.mutate();
  };

  return (
    <AuthLayout title="Forgot your password?" subtitle="Enter your email and we'll send you a link to choose a new one.">
      {mutation.isSuccess ? (
        <div style={{ display: "grid", gap: 16 }}>
          <Alert tone="success" title="Check your inbox">{mutation.data.message}</Alert>
          <Button variant="primary" size="lg" block onClick={onBack}>Back to log in</Button>
        </div>
      ) : (
        <form onSubmit={submit} noValidate>
          {mutation.isError && <div style={{ marginBottom: 16 }}><ErrorState title="Couldn't send the link" message={mutation.error.message} /></div>}
          <Field label="Email" type="email" autoComplete="email" placeholder="you@example.com" value={email}
            onChange={(e) => setEmail(e.target.value)} error={touched ? emailError || undefined : undefined} />
          <Button type="submit" variant="primary" size="lg" block loading={mutation.isPending}>
            {mutation.isPending ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
      {!mutation.isSuccess && <p className="auth-foot"><button type="button" className="link-btn" onClick={onBack}>Back to log in</button></p>}
    </AuthLayout>
  );
}
