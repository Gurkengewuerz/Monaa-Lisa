import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { Prisma } from '@prisma/client';
import { CreatePaperDto } from './dto/create-paper.dto';
import { UpdatePaperDto } from './dto/update-paper.dto';
import { QueryPaperDto } from './dto/query-paper.dto';

/**
 * PapersService Nico
 * -------------------------------
 * Kümmert sich um alles rund um "Paper":
 * - Anlegen & Upserten (für idempotente Ingestion)
 * - Suchen & Paginieren
 * - Lesen, Updaten, Löschen
 *
 * Hinweis: Wir normalisieren Datumsfelder mit `new Date(...)`
 * und setzen serverseitig ein `added`-Timestamp.
 */
@Injectable()
export class PapersService {
  constructor(private prisma: PrismaService) {}

  /**
   * Legt ein neues Paper an.
   * - `published` ist optional → wenn nicht da, speichern wir `null`
   * - `added` ist der Zeitpunkt, zu dem wir es in unser System aufnehmen
   */
  async create(dto: CreatePaperDto) {
    return this.prisma.paper.create({
      data: {
        entry_id: dto.entry_id,
        title: dto.title,
        authors: authorsToString(dto.authors) ?? null,
        abstract: dto.abstract ?? null,
        categories: dto.categories ?? null,
        published: dto.published ? new Date(dto.published) : null,
        updated: dto.updated ? new Date(dto.updated) : null,
        doi: dto.doi ?? null,
        journal_ref: dto.journal_ref ?? null,
        license: dto.license ?? null,
        url: dto.url ?? null,
        s2_id: dto.s2_id ?? null,
        non_arxiv_citation_count: dto.non_arxiv_citation_count ?? null,
        non_arxiv_reference_count: dto.non_arxiv_reference_count ?? null,
      },
    });
  }

  // Idempotente Ingestion: Upsert über entry_id
  /**
   * Upsert (Create ODER Update) anhand `entry_id`.
   * Warum? Ingestion kann dasselbe Item mehrfach sehen – hiermit vermeiden wir Duplikate.
   */
  async upsertByEntryId(dto: CreatePaperDto) {
    return this.prisma.paper.upsert({
      where: { entry_id: dto.entry_id },
      update: {
        title: dto.title,
        authors: authorsToString(dto.authors) ?? null,
        abstract: dto.abstract ?? null,
        categories: dto.categories ?? null,
        published: dto.published ? new Date(dto.published) : null,
        updated: dto.updated ? new Date(dto.updated) : null,
        doi: dto.doi ?? null,
        journal_ref: dto.journal_ref ?? null,
        license: dto.license ?? null,
        url: dto.url ?? null,
        s2_id: dto.s2_id ?? null,
        non_arxiv_citation_count: dto.non_arxiv_citation_count ?? null,
        non_arxiv_reference_count: dto.non_arxiv_reference_count ?? null,
      },
      create: {
        entry_id: dto.entry_id,
        title: dto.title,
        authors: authorsToString(dto.authors) ?? null,
        abstract: dto.abstract ?? null,
        categories: dto.categories ?? null,
        published: dto.published ? new Date(dto.published) : null,
        updated: dto.updated ? new Date(dto.updated) : null,
        doi: dto.doi ?? null,
        journal_ref: dto.journal_ref ?? null,
        license: dto.license ?? null,
        url: dto.url ?? null,
        s2_id: dto.s2_id ?? null,
        non_arxiv_citation_count: dto.non_arxiv_citation_count ?? null,
        non_arxiv_reference_count: dto.non_arxiv_reference_count ?? null,
      },
    });
  }

  /**
   * Sucht Papers mit Volltext-Like über `title`, `authors`, `summary`,
   * plus optionaler Kategorie & Datumsbereich.
   * Pagination via `skip`/`take`, dazu Gesamtanzahl für UI.
   */
  // `MonaaLisa/src/Backend/src/papers/papers.service.ts`

async findMany(q: QueryPaperDto) {
  const skip = toNumber(q.skip, 0);
  const take = toNumber(q.take, 20);

  // ── sort=citations → raw SQL path (order by citation count DESC) ──
  if (q.sort === 'citations' && q.categories && !q.search && !q.dateFrom && !q.dateTo) {
    return this.findManyByCitationCount(q.categories, skip, take);
  }

  const where: Prisma.PaperWhereInput = {};

  // Stub-Titel grundsätzlich ausschließen
  where.NOT = [
    { title: { equals: '[STUB] Pending Fetch', mode: 'insensitive' } },
  ];

  if (q.search) {
    const searchTerm = q.search.trim();
    where.OR = [
      { title: { contains: searchTerm, mode: 'insensitive' } },
      { authors: { contains: searchTerm, mode: 'insensitive' } },
      { abstract: { contains: searchTerm, mode: 'insensitive' } },
    ];
  }

  if (q.categories) where.categories = { contains: q.categories };

  if (q.dateFrom || q.dateTo) {
    const publishedFilter: Prisma.DateTimeNullableFilter = {};
    if (q.dateFrom) publishedFilter.gte = new Date(q.dateFrom);
    if (q.dateTo) publishedFilter.lte = new Date(q.dateTo);
    where.published = publishedFilter;
  }

  const [items, total] = await this.prisma.$transaction([
    this.prisma.paper.findMany({
      where,
      orderBy: [{ published: 'desc' }, { added: 'desc' }],
      skip,
      take,
    }),
    this.prisma.paper.count({ where }),
  ]);

  return { items, total, skip, take };
}

  /**
   * Holt ein Paper per `entry_id`.
   * Wirft, wenn es die ID nicht gibt → bewusst, damit der Caller entscheiden kann.
   */
  async findByEntryId(entry_id: string) {
    return this.prisma.paper.findUniqueOrThrow({ where: { entry_id } });
  }

  /**
   * Aktualisiert ein Paper per `entry_id`.
   * - Nur Felder überschreiben, die explizit kommen.
   * - `published`: wenn nicht gesetzt, bleibt der vorhandene Wert (via `undefined`)
   */
  async updateByEntryId(entry_id: string, dto: UpdatePaperDto) {
    return this.prisma.paper.update({
      where: { entry_id },
      data: {
        title: dto.title,
        authors:
          dto.authors === undefined ? undefined : authorsToString(dto.authors),
        abstract: dto.abstract,
        categories: dto.categories,
        published: dto.published ? new Date(dto.published) : undefined,
        updated: dto.updated ? new Date(dto.updated) : undefined,
        doi: dto.doi,
        journal_ref: dto.journal_ref,
        license: dto.license,
        url: dto.url,
        s2_id: dto.s2_id,
        non_arxiv_citation_count: dto.non_arxiv_citation_count,
        non_arxiv_reference_count: dto.non_arxiv_reference_count,
      },
    });
  }

  /**
   * Batch-Fetch: holt mehrere Papers anhand einer Liste von `entry_id`s.
   * Maximal 5000 Ergebnisse.
   */
  async findByEntryIds(entryIds: string[], take = 5000) {
    const papers = await this.prisma.paper.findMany({
      where: { entry_id: { in: entryIds } },
      take,
    });
    return this.enrichWithCitations(papers);
  }

  /**
   * Holt aus der paper_citation-Tabelle die cited_paper_entry_ids für
   * jedes übergebene Paper und hängt sie als `citations: string[]` an.
   */
  private async enrichWithCitations<T extends { entry_id: string }>(papers: T[]): Promise<(T & { citations: string[] })[]> {
    if (!papers.length) return [];

    const entryIds = papers.map(p => p.entry_id);
    const rows = await this.prisma.paperCitation.findMany({
      where: { belonging_paper_entry_id: { in: entryIds } },
      select: { belonging_paper_entry_id: true, cited_paper_entry_id: true },
    });

    const citationMap = new Map<string, string[]>();
    for (const r of rows) {
      const arr = citationMap.get(r.belonging_paper_entry_id);
      if (arr) arr.push(r.cited_paper_entry_id);
      else citationMap.set(r.belonging_paper_entry_id, [r.cited_paper_entry_id]);
    }

    return papers.map(p => ({
      ...p,
      citations: citationMap.get(p.entry_id) ?? [],
    }));
  }

  /**
   * Löscht ein Paper per `entry_id`.
   * Keine Magie – weg ist weg.
   */
  async deleteByEntryId(entry_id: string) {
    return this.prisma.paper.delete({ where: { entry_id } });
  }
}


/**
 *
 * Konvertiert einen unbekannten Wert in eine endliche Zahl, wobei der angegebene Fallback zurückgegeben wird, wenn die Konvertierung nicht möglich ist.
 */
function toNumber(value: unknown, fallback: number): number {
  const parsed =
    typeof value === 'string' && value.trim() !== ''
      ? Number(value)
      : typeof value === 'number'
        ? value
        : NaN;

  if (Number.isFinite(parsed)) {
    return parsed;
  }
  return fallback;
}

/**
 * Wandelt ein array von authors (string[]) in einen einzelnen String um, welcher im Frontend dann angezeigt werden kann
 * @param authors Array von Autoren
 * @returns Autoren konkateniert
 */
function authorsToString(
  authors: string[] | string | null | undefined,
): string {
  if (authors == null) return '';
  return Array.isArray(authors) ? authors.join(', ') : authors;
}