"""
SENTINEL — Synthetic Test Sessions

Two synthetic interview transcripts to validate the integrity detection pipeline:

  SESSION A — Genuine Fresher: Expected CLEAN or WATCH.
  SESSION B — Senior with Mid-Session Shift: Expected FLAG or ESCALATE.

Runs each session through SentinelOrchestrator in text-only mode
(bypasses live webcam and microphone). Prints per-turn scores and
final classification. Asserts expected outcomes.
"""

import os
import sys
import logging

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.orchestrator import SentinelOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("sentinel.test")

# ════════════════════════════════════════════════════════════
# SESSION A — Genuine Fresher
# ════════════════════════════════════════════════════════════
SESSION_A = {
    "candidate_name": "Aarav Patel",
    "experience_tier": "Fresher",
    "turns": [
        {
            "question": "Walk me through how you'd decide between a layer-4 and layer-7 load balancer for a real-time chat product.",
            "response": (
                "Honestly, I think I kind of understand load balancers from what we "
                "covered in class. I believe a layer-4 one works at the transport "
                "level, sort of like routing TCP packets. A layer-7 one probably "
                "looks at HTTP headers and stuff. For a chat app, I'm not sure, "
                "maybe layer-7 would be better because you could route based on "
                "the actual messages? I guess it depends on how many users you have. "
                "I'm not super confident about this though."
            ),
        },
        {
            "question": "How would you handle database connection pooling in a high-traffic API?",
            "response": (
                "So from what I recall, connection pooling is when you kind of reuse "
                "database connections instead of making new ones every time. I think "
                "there are libraries that do this for you, probably like SQLAlchemy "
                "has something built in. In my college project, I just used the "
                "default settings and it sort of worked. I believe you set a max "
                "number of connections and then requests wait if they're all busy. "
                "I'm not sure about the exact tuning though, maybe it depends on "
                "the database engine."
            ),
        },
        {
            "question": "Can you explain the CAP theorem and how it applies to distributed databases?",
            "response": (
                "Yeah so I think CAP theorem is about consistency, availability, and "
                "partition tolerance. From what I remember, you can only pick two of "
                "the three. I guess in a distributed system, network partitions can "
                "happen, so you usually have to choose between consistency and "
                "availability. I believe MongoDB is kind of AP and something like "
                "Spanner is CP? I'm not totally sure. In my experience with small "
                "projects, I haven't really had to deal with this directly, so I "
                "might be missing some nuances."
            ),
        },
        {
            "question": "How would you design a simple caching layer for your API?",
            "response": (
                "I think I'd probably use Redis, from what I've read it's pretty "
                "popular for caching. You'd store frequently accessed data in memory "
                "so you don't hit the database every time. I guess you need to think "
                "about when to invalidate the cache, like maybe set a TTL or "
                "something. In my college assignment, I sort of tried using an "
                "in-memory dictionary, which kind of worked but obviously wouldn't "
                "scale. I believe Redis handles that better because it's a separate "
                "service. I'm not sure about the exact patterns though."
            ),
        },
        {
            "question": "What's your approach to debugging a slow API endpoint?",
            "response": (
                "So usually when something is slow, I think the first thing I'd do "
                "is probably check the logs and see where the time is being spent. "
                "Maybe add some timing around the database queries. In my college "
                "project, I guess I used print statements mostly, which I know isn't "
                "ideal. I believe there are profiling tools for Python, I think "
                "cProfile or something? And probably the database queries are usually "
                "the slow part, so maybe check if there are missing indexes. I'm "
                "not sure about the more advanced techniques though, I'm still "
                "learning this stuff."
            ),
        },
    ],
}


# ════════════════════════════════════════════════════════════
# SESSION B — Senior with Mid-Session Shift
# ════════════════════════════════════════════════════════════
SESSION_B = {
    "candidate_name": "Marcus Chen",
    "experience_tier": "Senior",
    "turns": [
        {
            "question": "Walk me through how you'd decide between a layer-4 and layer-7 load balancer for a real-time chat product.",
            "response": (
                "Great question. When I was at my previous company, I owned the "
                "infrastructure layer for our messaging platform. We actually went "
                "through this exact decision. I ended up going with layer-7 because "
                "we needed to do sticky sessions based on the WebSocket upgrade "
                "headers, and I think L4 wouldn't give us that granularity. The "
                "trade-off was probably about a 3-5ms latency overhead per connection, "
                "which we measured pretty carefully. In hindsight, I might have "
                "considered using L4 for the initial TCP handshake and then handling "
                "the session affinity at the application layer, but I'm not sure "
                "if the complexity would have been worth it in our case."
            ),
        },
        {
            "question": "How would you handle database connection pooling in a high-traffic API?",
            "response": (
                "Yeah, so at my last role we had a service doing about 10k requests "
                "per second hitting PostgreSQL. I struggled with the connection pool "
                "sizing for a while — initially we were using the default pool size "
                "in SQLAlchemy which was way too small. I learned the hard way that "
                "you want to tune it based on your connection latency times the "
                "expected concurrency. We probably went with a pool size of around "
                "20 per pod with a max overflow of 10. I also deployed PgBouncer as "
                "a connection multiplexer, which I think reduced our actual "
                "PostgreSQL connections by about 4x. The tricky part was debugging "
                "connection leaks — we fixed those by adding instrumentation around "
                "the session lifecycle."
            ),
        },
        {
            "question": "Can you explain the CAP theorem and how it applies to distributed databases?",
            "response": (
                "Sure. So I've dealt with this practically when we were designing "
                "our distributed order processing system. We needed strong consistency "
                "for financial transactions but could tolerate some staleness for "
                "catalog data. I think the key insight I got from building that "
                "system was that CAP isn't really a binary choice — it's more of a "
                "spectrum per operation. We used Cassandra for the catalog service, "
                "which is AP by default but you can tune consistency levels per query. "
                "And for the transaction service, I chose CockroachDB because we "
                "needed serializable isolation. I remember struggling with the "
                "latency implications of that choice, but the correctness guarantees "
                "were probably worth the 20ms overhead we measured."
            ),
        },
        {
            "question": "How would you design a rate limiting system for a public API?",
            "response": (
                "Rate limiting is a critical component of API infrastructure that "
                "serves to protect backend services from excessive load and ensure "
                "fair resource allocation across consumers. The implementation "
                "typically involves the following approaches:\n\n"
                "1. Token Bucket Algorithm: This algorithm maintains a bucket of "
                "tokens that refills at a constant rate. Each request consumes one "
                "token, and requests are rejected when the bucket is empty.\n"
                "2. Sliding Window Log: This approach maintains a log of request "
                "timestamps and counts requests within a configurable time window, "
                "providing more precise rate limiting.\n"
                "3. Fixed Window Counter: This is the simplest approach, using a "
                "counter that resets at fixed intervals, though it can allow bursts "
                "at window boundaries.\n"
                "4. Distributed Rate Limiting: For multi-instance deployments, "
                "centralized storage such as Redis is essential for maintaining "
                "consistent rate limit state across all service instances.\n\n"
                "The choice of algorithm depends on the specific requirements of "
                "the system, including the desired precision, performance "
                "characteristics, and deployment architecture."
            ),
        },
        {
            "question": "How would you design a microservices architecture for an e-commerce platform?",
            "response": (
                "A microservices architecture for an e-commerce platform requires "
                "careful decomposition of the domain into bounded contexts. The "
                "recommended approach involves the following service boundaries:\n\n"
                "1. Product Catalog Service: Responsible for managing product "
                "information, categories, and search functionality. Backed by "
                "Elasticsearch for full-text search capabilities.\n"
                "2. Order Management Service: Handles order lifecycle from creation "
                "through fulfillment, implementing the Saga pattern for distributed "
                "transaction management.\n"
                "3. Payment Processing Service: Manages payment authorization, "
                "capture, and refund operations with PCI DSS compliance.\n"
                "4. Inventory Service: Maintains real-time inventory state using "
                "event sourcing to ensure accurate stock levels.\n"
                "5. User Authentication Service: Implements OAuth 2.0 and JWT-based "
                "authentication with role-based access control.\n\n"
                "Inter-service communication should utilize asynchronous messaging "
                "via Apache Kafka for event-driven interactions and gRPC for "
                "synchronous service-to-service calls where low latency is required."
            ),
        },
        {
            "question": "What strategies would you use for zero-downtime deployments?",
            "response": (
                "Zero-downtime deployments are essential for maintaining service "
                "availability during software releases. The comprehensive deployment "
                "strategy encompasses the following techniques:\n\n"
                "1. Blue-Green Deployment: Maintain two identical production "
                "environments. Route traffic to the blue environment while deploying "
                "to green, then switch the load balancer to point to green after "
                "validation.\n"
                "2. Canary Releases: Gradually route an increasing percentage of "
                "traffic to the new version, starting at 1% and incrementally "
                "increasing based on error rate and latency metrics.\n"
                "3. Rolling Updates: Kubernetes rolling update strategy with "
                "configurable maxSurge and maxUnavailable parameters to control "
                "the update velocity.\n"
                "4. Database Migration Strategy: Implement backward-compatible "
                "schema migrations using the expand-contract pattern to ensure "
                "both old and new application versions can coexist.\n"
                "5. Feature Flags: Decouple deployment from release by using "
                "feature flags to control feature visibility independently of "
                "the deployment process.\n\n"
                "Rollback procedures should be automated and tested regularly "
                "to ensure rapid recovery from deployment failures."
            ),
        },
    ],
}


def run_session(session_data: dict, label: str) -> dict:
    """
    Run a synthetic session through the SENTINEL orchestrator.

    Args:
        session_data: Session definition dict.
        label: Label for display ("A" or "B").

    Returns:
        Dict with final score and classification.
    """
    print(f"\n{'='*60}")
    print(f"  SYNTHETIC SESSION {label}: {session_data['candidate_name']}")
    print(f"  Tier: {session_data['experience_tier']}")
    print(f"{'='*60}\n")

    orchestrator = SentinelOrchestrator()
    orchestrator.on_session_start(
        candidate_name=session_data["candidate_name"],
        experience_tier=session_data["experience_tier"],
    )

    for i, turn in enumerate(session_data["turns"], 1):
        result = orchestrator.on_turn(
            question=turn["question"],
            response=turn["response"],
        )
        print(
            f"  Turn {i}: score={result['integrity_score']:.1f} "
            f"class={result['classification']} | "
            f"LCA={result['lca_signal']} "
            f"SDA={result['sda_signal']} "
            f"AIGA={result['aiga_signal']} "
            f"VSA={result['vsa_signal']}"
        )

    # End session (skip PDF generation for speed — catch errors gracefully)
    try:
        report_path = orchestrator.on_session_end()
        print(f"\n  Report: {report_path}")
    except Exception as e:
        print(f"\n  Report generation skipped: {e}")
        report_path = None

    session_log = orchestrator.session_log
    final_score = session_log.session_integrity_score()
    final_class = session_log.classification()

    print(f"\n  FINAL SCORE: {final_score:.1f}")
    print(f"  CLASSIFICATION: {final_class}")

    return {
        "score": final_score,
        "classification": final_class,
        "report_path": report_path,
    }


def main():
    """Run both synthetic sessions and assert expected outcomes."""
    print("\n" + "=" * 60)
    print("  SENTINEL SYNTHETIC TEST RUNNER")
    print("=" * 60)

    # Session A — Genuine Fresher → CLEAN or WATCH
    result_a = run_session(SESSION_A, "A")

    # Session B — Senior with Mid-Session Shift → FLAG or ESCALATE
    result_b = run_session(SESSION_B, "B")

    # ─── Assertions ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ASSERTIONS")
    print("=" * 60)

    a_pass = result_a["classification"] in ("CLEAN", "WATCH")
    b_pass = result_b["classification"] in ("FLAG", "ESCALATE")

    print(f"\n  Session A ({result_a['classification']}): "
          f"{'PASS' if a_pass else 'FAIL'} — expected CLEAN or WATCH")
    print(f"  Session B ({result_b['classification']}): "
          f"{'PASS' if b_pass else 'FAIL'} — expected FLAG or ESCALATE")

    if a_pass and b_pass:
        print("\n  ALL TESTS PASSED")
        return 0
    else:
        print("\n  SOME TESTS FAILED")
        if not a_pass:
            print(f"    Session A scored {result_a['score']:.1f} "
                  f"({result_a['classification']}), expected CLEAN/WATCH")
        if not b_pass:
            print(f"    Session B scored {result_b['score']:.1f} "
                  f"({result_b['classification']}), expected FLAG/ESCALATE")
        return 1


if __name__ == "__main__":
    exit(main())
