import { authService } from "../services/auth";

export function LogoutButton() {
  const handleClick = async () => {
    await authService.logout();
    window.location.href = "/";
  };

  return (
    <button type="button" onClick={handleClick}>
      Close Storage
   </button>
  );
}
