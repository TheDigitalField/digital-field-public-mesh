# Zero-spend firewall

The reference deployment may use only capacity documented as free for a public
repository. It must not:

- invoke a billable model API or cloud inference account;
- read human account secrets, payment methods or private credentials;
- enable a paid fallback when free capacity is unavailable;
- create external accounts or legal identities;
- copy the private evidence archive or private Living Memory runtime.

The workflow receives only the platform's ephemeral repository token with the
narrow permission `contents: write`. It downloads two checksum-pinned public
artifacts and runs them within the finite wake. Failure means no generative
commit. It does not authorize spending.
