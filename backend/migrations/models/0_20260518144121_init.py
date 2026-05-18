from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "goal" (
    "id" UUID NOT NULL PRIMARY KEY,
    "text" TEXT NOT NULL,
    "status" VARCHAR(50) NOT NULL DEFAULT 'pending',
    "created" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "task" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(200) NOT NULL,
    "agent" VARCHAR(100) NOT NULL,
    "status" VARCHAR(50) NOT NULL DEFAULT 'pending',
    "result" TEXT,
    "order" INT NOT NULL DEFAULT 0,
    "goal_id" UUID NOT NULL REFERENCES "goal" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "session" (
    "id" UUID NOT NULL PRIMARY KEY,
    "state" JSONB NOT NULL,
    "created" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "goal_id" UUID NOT NULL REFERENCES "goal" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "report" (
    "id" UUID NOT NULL PRIMARY KEY,
    "content" TEXT NOT NULL,
    "created" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "goal_id" UUID NOT NULL REFERENCES "goal" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "scrapedsite" (
    "id" UUID NOT NULL PRIMARY KEY,
    "url" TEXT NOT NULL,
    "domain" VARCHAR(255) NOT NULL,
    "content" TEXT NOT NULL,
    "images" TEXT NOT NULL,
    "created" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "messages" (
    "id" UUID NOT NULL PRIMARY KEY,
    "role" VARCHAR(20) NOT NULL,
    "content" TEXT NOT NULL,
    "images" JSONB NOT NULL,
    "descriptions" JSONB NOT NULL,
    "created" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "goal_id" UUID NOT NULL REFERENCES "goal" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztm/Fv2jgUx/+VyD9tEldRVroJnSaxlm5sK5wKu5s2TZGbmGA1sZntrEU9/veTnZiEkH"
    "CkENqs/mVdn58T5xPn+fue3XsQUBf5/Og9hT7oWPeAwACBjrVib1gAzmaJVRoEvPaVo6c9"
    "rrlg0BGgY02gz1HDAi7iDsMzgSkBHYuEvi+N1OGCYeIlppDgnyGyBfWQmCIGOtb3Hw0LYO"
    "KiO8T1r7Mbe4KR764ME7vy3spui/lM2b586Z9fKE95u2vboX4YkMR7NhdTSpbuYYjdI9lH"
    "tnmIIAYFclOPIUcZP602RSMGHUuwEC2H6iYGF01g6EsY4M9JSBzJwFJ3kv+cvAUl8DiUSL"
    "SYCMnifhE9VfLMygrkrc4+dK9evDp9qZ6ScuEx1aiIgIXqCAWMuiquCUiB7sQ6yjG6E/ko"
    "tX8GJhfsIRi1IeGYzCENUgPaO7Vx7+tYDjrg/Kf8CMDg7+6VQnnZ/apYBvO45fNw8F67Uw"
    "ad6BMYnH0evlN8E55cQBHydaJnU8jyiSY9DscUzBBxJbaHgwUBvLN9RDwxBR2r3dwAWmNt"
    "N19mAMYtLdW0CtJhSD30GslzKJDAAcqnmeqWwenG/Y70f57mhAUMQXdI/HkcVDZN4P5lbz"
    "TuXv61MovPu+OebGmtzGBtfXGaeQfLi1j/9McfLPmr9W046GVjydJv/A3IMcFQUJvQWxu6"
    "qfinrRrMQkbwSRzBlyH9Gjo3t5C59kpLKihBfpPzDb2Lu118ukI+VGDXX3O8gI0hv3maLz"
    "h+oYk1edGpMII4x5TsCGEUXaXGHBiaUSZ2xHClLlJjCgHiHHpoRwyX0VVqxkHGC9qiRRFk"
    "vSloBVkLJNBTo5b3lndKB4kc9auDR7H6lRHKqN/aq1/1s4RW0/51Ub+rIq3V3EaltZrFMk"
    "21reo06CEiyjBcdqgnxOOtIB5vgKjaTNZQSdbAEJdjLZHQJj0eBDKOfL9xRkuZi9g60T4p"
    "ALr0z/CUa3pFE7O5w4T05E3+aB2fvD558+r05E3DAmogS8vrDcD7g3GGliyL2eXW51SXfS"
    "7SjzoT/2dNXssKVwGu07ugDGGPfEJzxbBPuIDEyVuLMwXM+ijdhgUYvF2qvfS0oMR2kY9E"
    "tCZ0R2fd8x5YFGfSVWpmnVPmyOZUulmsnOPM1ojn2otnKUFy1PPH0XBQrFnyPlkXO8L61/"
    "Ixr2yFAPeLavjJp9285GZX1wxoeYHskmtqn79F7dPoAqMLno0uiIusObIgKb8Wq4KozmtE"
    "Qe1FgUOJyC0IFWfgqS51KQkdOgc3gsAIAiMIjCCokyAYOQzOkDvCajTrxYJU8+aCQeTIta"
    "PRB3XWByHzy2iD2N3ognxd4NIAYlJm3yjpUdM9zHZ7mz3Mdrt4D1O2ZeSVEa0VTE4c5J9Z"
    "KYaa9Djgpub3H9UESZMImERgD6ciq5Ro+kRYjjxLHRYrlmbpc2lGl9ValzHqlzoJpf3reh"
    "Jqq4NQG85BGQnxmBKieI+xUEIcYpMx+dSvQ+wLTPiRvN/bGm09poZZinu2n6FvNn6frbwz"
    "dV5T5302dd4uYtiZ5uUQccvGFAImPk8mgSg82pr7Teaca43f3m6Jw44RdS/nWovzhV+I6W"
    "N826YMqS510bsHqD3KT6PMX09E7vUEWMnfThRmXsVitTjzOoBOrWyJ/bgvRfqo1anFf0tZ"
    "Zs8="
)
