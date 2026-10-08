import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { resetPassword } from "./api";
import AuthLayout from "./AuthLayout";
import Field from "./ui/Field";
import { Alert, Button, ErrorState } from "./ui/primitives";

const MIN_PASSWORD = 8;

export default function ResetPassword({ token, onDone }: { token: string; onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState(false);
  const mutation = useMutation({ mutationFn: () => resetPassword(token, password) });

  const passwordError = password.length >= MIN_PASSWORD ? "" : `Use at least ${MIN_PASSWORD} characters.`;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!passwordError) mutation.mutate();
  };

  return (
    <AuthLayout title="Choose a new password" subtitle="This link can only be used once.">
      {mutation.isSuccess ? (
        <div style={{ display: "grid", gap: 16 }}>
          <Alert tone="success" title="Password updated">{mutation.data.message}</Alert>
          <Button variant="primary" size="lg" block onClick={onDone}>Go to log in</Button>
        </div>
      ) : (
        <form onSubmit={submit} noValidate>
          {mutation.isError && <div style={{ marginBottom: 16 }}><ErrorState title="Couldn't update your password" message={mutation.error.message} /></div>}
          <Field label="New password" type="password" autoComplete="new-password" placeholder="At least 8 characters" value={password}
            onChange={(e) => setPassword(e.target.value)} hint={`Minimum ${MIN_PASSWORD} characters.`}
            error={touched ? passwordError || undefined : undefined} />
          <Button type="submit" variant="primary" size="lg" block loading={mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Update password"}
          </Button>
        </form>
      )}
      {!mutation.isSuccess && <p className="auth-foot"><button type="button" className="link-btn" onClick={onDone}>Back to log in</button></p>}
    </AuthLayout>
  );
}
