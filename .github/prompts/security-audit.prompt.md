# Security Audit Prompt

Use this prompt to perform security reviews and vulnerability assessments.

## Prompt

```
Perform a comprehensive security audit of [FILE/MODULE/ENDPOINT] covering:

OWASP Top 10 Check:
1. [ ] Broken Access Control
   - Authentication on all protected endpoints
   - Authorization checks before data access
   - Proper session management

2. [ ] Cryptographic Failures
   - Secrets not hardcoded
   - Sensitive data encrypted at rest/in transit
   - Strong encryption algorithms used
   - Secure key management

3. [ ] Injection Attacks
   - SQL injection prevention (parameterized queries)
   - NoSQL injection prevention
   - Command injection prevention
   - Log injection prevention

4. [ ] Insecure Design
   - Rate limiting implemented
   - Input validation on all inputs
   - Output encoding
   - Security by default

5. [ ] Security Misconfiguration
   - No debug mode in production
   - Error messages don't leak info
   - Security headers present
   - Default credentials changed

6. [ ] Vulnerable Components
   - Dependencies up to date
   - No known CVEs in dependencies
   - Regular security updates

7. [ ] Authentication Failures
   - Strong password policies
   - Multi-factor authentication
   - Account lockout after failed attempts
   - Session timeout configured

8. [ ] Data Integrity Failures
   - Digital signatures verified
   - CI/CD pipeline secure
   - No unsigned packages

9. [ ] Logging & Monitoring Failures
   - Security events logged
   - No sensitive data in logs
   - Log retention policy
   - Alerting configured

10. [ ] Server-Side Request Forgery
    - URL validation
    - Whitelist allowed domains
    - Network segmentation

API Security:
- [ ] Input validation (Pydantic schemas)
- [ ] Rate limiting on endpoints
- [ ] CORS configured properly
- [ ] Authentication required
- [ ] Authorization checks
- [ ] Request size limits
- [ ] Timeout configurations

Docker Security:
- [ ] Non-root user (USER 1000:1000)
- [ ] No secrets in ENV variables
- [ ] BuildKit secrets for build-time
- [ ] Minimal base image (slim/alpine)
- [ ] Image scanning for vulnerabilities
- [ ] Read-only root filesystem
- [ ] No privileged mode

Python Security:
- [ ] No eval() or exec() usage
- [ ] No pickle with untrusted data
- [ ] No shell=True in subprocess
- [ ] Path traversal prevention
- [ ] XML external entity prevention

Secrets Management:
- [ ] Secrets in Azure Key Vault (production)
- [ ] .env for local development only
- [ ] .env in .gitignore
- [ ] BuildKit secrets for Artifactory
- [ ] No secrets in code/comments/logs

Provide:
1. Security risk rating (Critical/High/Medium/Low)
2. List of vulnerabilities found
3. Remediation steps for each issue
4. Code examples of secure alternatives
5. Priority order for fixes
```

## Example Usage

```
Perform a comprehensive security audit of src/sidiap_azure_devops_agent/api/workflows.py covering:
[... rest of prompt ...]
```

## Related
- Agent: @senior-security-engineer
- Instructions: python.instructions.md, api.instructions.md, docker.instructions.md
