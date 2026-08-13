// Phase 2: JWT / Supabase auth middleware
// Currently a no-op passthrough for MVP (Phase 1)

export function requireAuth(req, res, next) {
  // TODO: validate Supabase JWT and attach req.user
  next();
}

export function optionalAuth(req, res, next) {
  // Attach user if header present, otherwise continue anonymously
  const auth = req.headers.authorization;
  if (!auth) return next();

  // TODO: verify token and attach req.user
  next();
}
