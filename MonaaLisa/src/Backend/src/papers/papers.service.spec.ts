/**
 * Nico August 2025
 */
import { Test, TestingModule } from '@nestjs/testing';
import { PapersService } from './papers.service';

describe('PaperService', () => {
  let service: PapersService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [PapersService],
    }).compile();

    service = module.get<PapersService>(PapersService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
