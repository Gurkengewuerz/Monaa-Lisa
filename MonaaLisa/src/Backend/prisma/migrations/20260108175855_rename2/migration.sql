-- CreateTable
CREATE TABLE "paper" (
    "id" SERIAL NOT NULL,
    "entry_id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "authors" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "published" TIMESTAMP(3),
    "category" TEXT,
    "url" TEXT,
    "hash" TEXT NOT NULL,
    "tsne" JSONB,
    "added" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "paper_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "paper_relation" (
    "source_id" TEXT NOT NULL,
    "target_id" TEXT NOT NULL,
    "confidence" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "paper_relation_pkey" PRIMARY KEY ("source_id","target_id")
);

-- CreateTable
CREATE TABLE "reference" (
    "id" SERIAL NOT NULL,
    "belonging_paper_entry_id" TEXT NOT NULL,
    "title" TEXT NOT NULL,

    CONSTRAINT "reference_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "embedding" (
    "id" SERIAL NOT NULL,
    "belonging_paper_entry_id" TEXT NOT NULL,
    "content" JSONB NOT NULL,

    CONSTRAINT "embedding_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "program_run" (
    "id" SERIAL NOT NULL,
    "start_date" TIMESTAMP(3) NOT NULL,
    "is_active" TEXT NOT NULL DEFAULT 'true',

    CONSTRAINT "program_run_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "historical_completion" (
    "id" SERIAL NOT NULL,
    "program_run_id" INTEGER NOT NULL,
    "category" TEXT NOT NULL,
    "start_date" TIMESTAMP(3) NOT NULL,
    "end_date" TIMESTAMP(3),
    "goal_oldest_paper_date" TIMESTAMP(3),
    "goal_reached" TEXT NOT NULL DEFAULT 'false',
    "reached_date" TIMESTAMP(3),
    "oldest_paper_date" TIMESTAMP(3),

    CONSTRAINT "historical_completion_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "paper_entry_id_key" ON "paper"("entry_id");

-- CreateIndex
CREATE UNIQUE INDEX "paper_hash_key" ON "paper"("hash");

-- CreateIndex
CREATE UNIQUE INDEX "embedding_belonging_paper_entry_id_key" ON "embedding"("belonging_paper_entry_id");
