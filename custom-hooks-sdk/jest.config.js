module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  transform: {
    "^.+\\.ts$": "ts-jest",
  },
  testPathIgnorePatterns: ["node_modules", "lib"],
  collectCoverageFrom: ["src/**/*.ts", "!src/__tests__/**"],
};
