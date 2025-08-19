/**
 * Nico August 2025
 */
import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { PrismaService } from './prisma/prisma.service';

// Das ist unser Modul. Module enthalten Struktur aber keinen Code selbst.
// Der typische ablauf ist Client->Controller->Service->(DB)->Service->Controller->Client
@Module({
  imports: [], // andere @Module die intern benötigt werdfen
  controllers: [AppController], // Alle Controller die dem Modul zugeordnet sind. Nimmt Requests an
  providers: [AppService, PrismaService], // Logik. Verwendet Datenbanken, Validierung usw. Wird vom Controller aufgerufen
})
export class AppModule {}
