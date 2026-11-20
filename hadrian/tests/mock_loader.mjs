export async function resolve(specifier, context, defaultResolve) {
  if (specifier === "@opencode/plugin") {
    return {
      url: new URL("./mock_plugin.mjs", import.meta.url).href,
      shortCircuit: true,
    };
  }
  return defaultResolve(specifier, context);
}
