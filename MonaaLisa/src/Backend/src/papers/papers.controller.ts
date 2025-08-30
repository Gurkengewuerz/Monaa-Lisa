/**
 * Nico - August 2025
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

  @Post()
  create(@Body() dto: CreatePaperDto) {
    return this.papers.create(dto);
  }

  @Post('upsert')
  upsert(@Body() dto: CreatePaperDto) {
    return this.papers.upsertByEntryId(dto);
  }

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

  @Delete(':entryId')
  remove(@Param('entryId') entryId: string) {
    return this.papers.deleteByEntryId(entryId);
  }
}
