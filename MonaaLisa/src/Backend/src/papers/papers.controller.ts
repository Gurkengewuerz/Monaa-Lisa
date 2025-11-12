/**
 * Nico - August 2025
 *
 * PapersController
 * -------------------------------
 * REST-Endpunkte rund um "Paper".
 * Der Controller ist schlank gehalten und delegiert alles an den Service.
 * Validierung/Transformation passiert über die DTOs (class-validator / class-transformer).
 */
import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  Query,
} from '@nestjs/common';
import { PapersService } from './papers.service';
import { CreatePaperDto } from './dto/create-paper.dto';
import { UpdatePaperDto } from './dto/update-paper.dto';
import { QueryPaperDto } from './dto/query-paper.dto';

@Controller('papers')
export class PapersController {
  constructor(private readonly papers: PapersService) {}

  /**
   * POST /papers
   * Legt ein neues Paper an.
   *
   * Erwartet: CreatePaperDto im Body.
   * Hinweis: Standard-HTTP-Code für POST ist 201 (Created), sofern nicht überschrieben.
   */
  @Post()
  create(@Body() dto: CreatePaperDto) {
    return this.papers.create(dto);
  }

  /**
   * POST /papers/upsert
   * Idempotente Ingestion: legt an oder aktualisiert anhand `entry_id`.
   *
   * Use-Case: Feeds/Importer, die dasselbe Item mehrfach sehen können.
   */
  @Post('upsert')
  upsert(@Body() dto: CreatePaperDto) {
    return this.papers.upsertByEntryId(dto);
  }

  // Nick - November 2025
  // Die Möglichkeiten mehrere Papers zu finden und anschließend im FE zu filtern soll gegeben sein
  @Get()
  findMany(@Query() q: QueryPaperDto) {
    return this.papers.findMany(q);
  }

  @Get(':entryId')
  findOne(@Param('entryId') entryId: string) {
    return this.papers.findByEntryId(entryId);
  }

  @Patch(':entryId')
  update(@Param('entryId') entryId: string, @Body() dto: UpdatePaperDto) {
    return this.papers.updateByEntryId(entryId, dto);
  }

  // Nick - November 2025
  // Die Möglichkeiten ein paper zu löschen damit es neugeladen werden kann
  @Delete(':entryId')
  remove(@Param('entryId') entryId: string) {
    return this.papers.deleteByEntryId(entryId);
  }
}
