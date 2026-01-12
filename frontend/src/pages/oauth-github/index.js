import { useEffect } from "react";

const OAuthGithub = () => {
  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");

    if (token) {
      localStorage.setItem("token", token);
      window.location.href = "/recipes"; // полная перезагрузка
    } else {
      window.location.href = "/signin";
    }
  }, []);

  return <p>Вход через GitHub...</p>;
};

export default OAuthGithub;
