/*
  Warnings:

  - You are about to drop the column `title` on the `reference` table. All the data in the column will be lost.
  - Added the required column `semanticscholar_obj` to the `reference` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "reference" DROP COLUMN "title",
ADD COLUMN     "semanticscholar_obj" JSONB NOT NULL;

-- CreateTable
CREATE TABLE "citation" (
    "id" SERIAL NOT NULL,
    "belonging_paper_entry_id" TEXT NOT NULL,
    "semanticscholar_obj" JSONB NOT NULL,

    CONSTRAINT "citation_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "paper_citation" (
    "belonging_paper_entry_id" TEXT NOT NULL,
    "cited_paper_entry_id" TEXT NOT NULL,

    CONSTRAINT "paper_citation_pkey" PRIMARY KEY ("belonging_paper_entry_id","cited_paper_entry_id")
);

-- CreateTable
CREATE TABLE "paper_reference" (
    "belonging_paper_entry_id" TEXT NOT NULL,
    "referenced_paper_entry_id" TEXT NOT NULL,

    CONSTRAINT "paper_reference_pkey" PRIMARY KEY ("belonging_paper_entry_id","referenced_paper_entry_id")
);

-- CreateIndex
CREATE INDEX "citation_belonging_paper_entry_id_idx" ON "citation"("belonging_paper_entry_id");

-- CreateIndex
CREATE INDEX "reference_belonging_paper_entry_id_idx" ON "reference"("belonging_paper_entry_id");
