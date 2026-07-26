import { LogoutButton } from "../components/LogoutButton";

type User = { id: number; created_at?: string; updated_at?: string };

export function HomePage({ user }: { user: User }) {
  return (
    <main className="home">
      <h1>Welcome to OmniDrive</h1>
      <p data-testid="user-id">User ID: {user.id}</p>
      <LogoutButton />
  </main>
  );
}
