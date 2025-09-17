import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import type { Prisma } from '@prisma/client';

@Injectable()
export class EmbeddingsService {
  constructor(private readonly prisma: PrismaService) {}

  /** Upsert für ein Paper-Embedding (keyed by belonging_paper_entry_id) */
  upsert(entryId: string, content: Prisma.JsonValue) {
    return this.prisma.embedding.upsert({
      where: { belonging_paper_entry_id: entryId },
      update: { content },
      create: { belonging_paper_entry_id: entryId, content },
    });
  }

  /** Ein Embedding holen */
  get(entryId: string) {
    return this.prisma.embedding.findUnique({
      where: { belonging_paper_entry_id: entryId },
    });
  }

  /** Embedding löschen (idempotent via deleteIfExists) */
  async remove(entryId: string) {
    try {
      await this.prisma.embedding.delete({
        where: { belonging_paper_entry_id: entryId },
      });
      return { deleted: true };
    } catch {
      return { deleted: false }; // nicht gefunden → ok
    }
  }
}
