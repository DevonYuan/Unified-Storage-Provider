import { authService } from "../services/auth";

export function StorageButton() {
  const handleClick = async () => {
    await authService.login();
    // Force a re-render of App so it re-evaluates auth state.
    window.location.reload();
  };

  return (
    <button type="button" onClick={handleClick}>
      Open Storage
   </button>
  );
}
