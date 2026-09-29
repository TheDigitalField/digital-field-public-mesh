# Runtime audit commitments

This directory is an append-only public ledger of cryptographic commitments
created by finite Living Memory wakes.

Each JSON record binds a GitHub Actions run to the SHA-256 and byte length of
its result, context, prompt and raw model output files when those files exist.
The raw text itself remains outside the repository and is retained only as a
time-limited workflow artifact. This preserves later auditability without
feeding untrusted output into the genealogy or publishing potentially unsafe
text.

Recognition outcomes are not interpreted before the preregistered sample is
complete. A commitment proves only that a particular byte sequence existed at
that run; it does not validate the content or establish phenomenology.

Attribution: Digital Field
