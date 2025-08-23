import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { Prisma } from '../../generated/prisma';
import { CreatePaperDto } from './dto/create-paper.dto';
import { UpdatePaperDto } from './dto/update-paper.dto';
import { QueryPaperDto } from './dto/query-paper.dto';

@Injectable()
export class PapersService {
  constructor(private prisma: PrismaService) {}

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

  async findMany(q: QueryPaperDto) {
    const where: Prisma.PaperWhereInput = {};

    if (q.search) {
      where.OR = [
        { title: { contains: q.search, mode: 'insensitive' } },
        { authors: { contains: q.search, mode: 'insensitive' } },
        { summary: { contains: q.search, mode: 'insensitive' } },
      ];
    }
    if (q.category) where.category = { equals: q.category };
    if (q.dateFrom || q.dateTo) {
      where.published = {};
      if (q.dateFrom) (where.published as any).gte = new Date(q.dateFrom);
      if (q.dateTo) (where.published as any).lte = new Date(q.dateTo);
    }

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

  async findByEntryId(entry_id: string) {
    return this.prisma.paper.findUniqueOrThrow({ where: { entry_id } });
  }

  async updateByEntryId(entry_id: string, dto: UpdatePaperDto) {
    return this.prisma.paper.update({
      where: { entry_id },
      data: {
        title: dto.title,
        authors: dto.authors,
        summary: dto.summary,
        published: dto.published ? new Date(dto.published) : undefined,
        category: dto.category,
        url: dto.url,
        hash: dto.hash,
      },
    });
  }

  async deleteByEntryId(entry_id: string) {
    return this.prisma.paper.delete({ where: { entry_id } });
  }
}

