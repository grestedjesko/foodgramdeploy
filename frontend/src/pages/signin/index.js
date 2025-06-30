import {
  Container,
  Input,
  Main,
  Form,
  Button,
  FormTitle,
} from "../../components";
import styles from "./styles.module.css";
import { useFormWithValidation } from "../../utils";
import { AuthContext } from "../../contexts";
import { Redirect } from "react-router-dom";
import { useContext } from "react";
import MetaTags from "react-meta-tags";

const SignIn = ({ onSignIn, submitError, setSubmitError }) => {
  const { values, handleChange, errors } = useFormWithValidation();
  const authContext = useContext(AuthContext);

  const onChange = (e) => {
    setSubmitError({ submitError: "" });
    handleChange(e);
  };

  const handleGithubLogin = () => {
    const apiRoot =
      process.env.REACT_APP_API_URL || // CRA
      import.meta.env?.VITE_API_URL || // Vite
      "";
    const url = `${apiRoot}/api/auth/github/login/`.replace(/([^:]\/)\/+/g, "$1");
    window.location.href = url;
  };

  if (localStorage.getItem("token")) {
    return <Redirect to="/recipes" />;
  }
  return (
    <Main withBG asFlex>
      <Container className={styles.center}>
        <MetaTags>
          <title>Войти на сайт</title>
          <meta
            name="description"
            content="Фудграм - Войти на сайт"
          />
          <meta property="og:title" content="Войти на сайт" />
        </MetaTags>
        <Form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            onSignIn(values);
          }}
        >
          <FormTitle>Войти</FormTitle>

          <Input
            required
            isAuth={true}
            name="email"
            placeholder="Email"
            onChange={onChange}
            error={errors}
          />
          <Input
            required
            isAuth={true}
            type="password"
            name="password"
            placeholder="Пароль"
            error={errors}
            submitError={submitError}
            onChange={onChange}
          />
          {/* <LinkComponent
            className={styles.link}
            href="/reset-password"
            title="Забыли пароль?"
          /> */}
          <Button modifier="style_dark" type="submit" className={styles.button}>
            Войти
          </Button>

          <button
              type="button"
              onClick={handleGithubLogin}
              className={styles.githubBtn}
          >
          <img
            src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            alt="GitHub"
            width="20"
            height="20"
          />
          Войти через GitHub
          </button>


        </Form>
      </Container>
    </Main>
  );
};

export default SignIn;
