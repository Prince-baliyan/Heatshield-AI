import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  getCurrentUser,
  getCsrfToken,
  login as loginRequest,
  logout as logoutRequest,
  type AuthUser,
} from "../services/api";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "ready"; user: AuthUser | null }
  | { status: "error"; user: null; message: string };

interface AuthContextValue {
  state: AuthState;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    status: "loading",
    user: null,
  });
  const requestVersion = useRef(0);

  useEffect(() => {
    let active = true;
    const version = requestVersion.current;
    getCurrentUser()
      .then(({ user }) => {
        if (active && requestVersion.current === version) {
          setState({ status: "ready", user });
        }
      })
      .catch((error: unknown) => {
        if (!active || requestVersion.current !== version) return;
        if (error instanceof ApiError && error.status === 401) {
          setState({ status: "ready", user: null });
        } else {
          setState({
            status: "error",
            user: null,
            message:
              error instanceof Error
                ? error.message
                : "Could not check the current sign-in session.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function authenticate(username: string, password: string) {
    const version = ++requestVersion.current;
    const { csrfToken } = await getCsrfToken();
    const response = await loginRequest(username, password, csrfToken);
    if (requestVersion.current === version) {
      setState({ status: "ready", user: response.user });
    }
  }

  async function endSession() {
    const version = ++requestVersion.current;
    await logoutRequest();
    if (requestVersion.current === version) {
      setState({ status: "ready", user: null });
    }
  }

  return (
    <AuthContext.Provider
      value={{ state, login: authenticate, logout: endSession }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return value;
}
