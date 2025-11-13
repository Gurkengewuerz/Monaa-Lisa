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
        authors: dto.authors,
        summary: dto.summary,
        published: dto.published ? new Date(dto.published) : null,
        category: dto.category ?? null,
        url: dto.url ?? null,
        hash: dto.hash,
        added: new Date(),
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
        authors: dto.authors,
        summary: dto.summary,
        published: dto.published ? new Date(dto.published) : null,
        category: dto.category ?? null,
        url: dto.url ?? null,
        hash: dto.hash,
      },
      create: {
        entry_id: dto.entry_id,
        title: dto.title,
        authors: dto.authors,
        summary: dto.summary,
        published: dto.published ? new Date(dto.published) : null,
        category: dto.category ?? null,
        url: dto.url ?? null,
        hash: dto.hash,
        added: new Date(),
      },
    });
  }

  /**
   * Sucht Papers mit Volltext-Like über `title`, `authors`, `summary`,
   * plus optionaler Kategorie & Datumsbereich.
   * Pagination via `skip`/`take`, dazu Gesamtanzahl für UI.
   */
  async findMany(q: QueryPaperDto) {
    const where: Prisma.PaperWhereInput = {};

    // Mini-Volltext: simpel, aber schnell & ausreichend für UI-Suche
    if (q.search) {
      where.OR = [
        { title: { contains: q.search, mode: 'insensitive' } },
        { authors: { contains: q.search, mode: 'insensitive' } },
        { summary: { contains: q.search, mode: 'insensitive' } },
      ];
    }
    if (q.category) where.category = { equals: q.category };

    // Datumsbereich (inklusive Grenzen)
    if (q.dateFrom || q.dateTo) {
      where.published = {};
      if (q.dateFrom) (where.published as any).gte = new Date(q.dateFrom);
      if (q.dateTo) (where.published as any).lte = new Date(q.dateTo);
    }

    // wir starten transaction damit keine verwaisten einträge entstehen und falls jemand auch ein paper erstellt oder löscht, count nicht pltz falsch ist
    const [items, total] = await this.prisma.$transaction([
      this.prisma.paper.findMany({
        where,
        orderBy: [{ published: 'desc' }, { added: 'desc' }],
        skip: q.skip,
        take: q.take,
      }),
      this.prisma.paper.count({ where }),
    ]);

    return { items, total, skip: q.skip, take: q.take };
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
        authors: dto.authors,
        summary: dto.summary,
        published: dto.published ? new Date(dto.published) : undefined, // Wichtig: nur setzen, wenn wirklich vorhanden – sonst bleibt DB-Wert unverändert.
        category: dto.category,
        url: dto.url,
        hash: dto.hash,
      },
    });
  }

  /**
   * Löscht ein Paper per `entry_id`.
   * Keine Magie – weg ist weg.
   */
  async deleteByEntryId(entry_id: string) {
    return this.prisma.paper.delete({ where: { entry_id } });
  }
}
