const STORAGE_KEY = "tyakxa.kronos.deviceConnection";

export const emptyKronosConnection = {
  deviceUrl: "",
  username: "admin",
  password: "",
  sessionTag: "",
  cookie: "",
  allowSelfSigned: false
};

export function loadKronosConnection() {
  try {
    return {
      ...emptyKronosConnection,
      ...JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}")
    };
  } catch {
    return { ...emptyKronosConnection };
  }
}

export function saveKronosConnection(connection) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(connection));
}