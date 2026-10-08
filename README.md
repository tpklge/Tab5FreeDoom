[Compilação de um clone novo](PUBLICATION.md) · [Licenças](THIRD_PARTY_NOTICES.md)

# Tab5Freedoom — M5Stack Tab5

Port de **Freedoom: Phase 1 e Phase 2**, derivado do
projeto local Tab5FinalDoom (commit-base ed2331e). Engine doomgeneric, ESP32-P4,
display ST7123, teclado Tab5/USB e áudio ES8388 preservados da base.
Freedoom 1 e 2 tiveram funcionamento confirmado pelo usuário no Tab5 em
2026-10-05, após habilitar nomes longos no FAT.

## Arquivos no microSD

Use FAT32 e coloque os dois IWADs na mesma pasta:

```
/doom/freedoom1.wad
/doom/freedoom2.wad
```

Também aceita FREEDOOM1.WAD e FREEDOOM2.WAD. Os WADs não são embutidos no firmware.
Use os jogos completos do [pacote oficial Freedoom 0.13.0](https://github.com/freedoom/freedoom/releases/download/v0.13.0/freedoom-0.13.0.zip).
Extraia os dois `.wad` do ZIP antes de copiá-los para o cartão.
Os exemplares baixados e verificados nesta sessão estão em
`downloads/freedoom-0.13.0/`, junto do checksum oficial e da licença.
O FAT usa suporte a nomes longos, necessário para os nove caracteres de
`freedoom1` e `freedoom2`, e para os diretórios de saves correspondentes.
Esta versão não procura WADs na raiz do cartão nem na flash.

## Menu de campanha

Ao ligar, a tela mostra Freedoom 1 e Freedoom 2 e a disponibilidade de cada arquivo.
Use **setas para cima/baixo** ou **1/2** para selecionar; **Enter** inicia a
campanha. Funciona com o Tab5 Keyboard ou teclado USB. **R** repete a busca
(e tenta montar o cartão se a montagem inicial falhou). O menu verifica que
cada arquivo abre e possui cabeçalho IWAD; o engine valida os demais dados.
Uma opção ausente/inválida não pode iniciar. Mesmo com só um WAD presente,
o menu aguarda confirmação. Ao sair pelo menu do jogo, o port salva as
configurações e reinicia o Tab5 para retornar à seleção de campanha.
A iluminação é apagada antes do reinício e acesa após desenhar o primeiro
quadro do menu, para ocultar a transição durante a inicialização do painel.
Um breve azul ainda pode aparecer antes de apagar; essa transição foi aceita
no projeto base Final Doom.
Não há controle por touch nesta versão.

Saves e configurações são separados automaticamente:

```
/doom/freedoom1/   # saves e default.cfg de Freedoom 1
/doom/freedoom2/   # saves e default.cfg de Freedoom 2
```

## Compilação

Use ESP-IDF **5.4.4**, alvo **esp32p4**:

```sh
idf.py build
```

O binário gerado é `build/Tab5Freedoom.bin`. A imagem SPIFFS legada foi
retirada do build; os IWADs são lidos somente do microSD. Com a tabela de
partições compatível já instalada no Tab5:

```sh
idf.py -p <porta> app-flash monitor
```

Para instalar bootloader, tabela e aplicativo:

```sh
idf.py -p <porta> flash monitor
```

Pelo M5Launcher, copie `build/Tab5Freedoom.bin` para a pasta `/APP` do
microSD e instale o aplicativo pelo launcher. Os WADs permanecem em `/doom`.

## Controles durante o jogo

- WASD ou setas: andar/girar.
- Ctrl: atirar. E ou Espaço: usar/abrir portas.
- Aa/Shift: correr. Alt + direção: deslocamento lateral.
- Enter: confirmar. Esc: menu. 1–7: armas.

Efeitos sonoros implementados; música ainda não implementada.

## Validação e compatibilidade

Build ESP-IDF 5.4.4 concluído; firmware em `build/Tab5Freedoom.bin`.
Build com nomes longos: 891584 bytes, 57% livres na partição de 2 MiB.
Os testes locais verificam oito cenários do menu e a ordem do encerramento:

```sh
python3 tests/test_menu.py
python3 tests/test_quit.py
```

Neste Mac, execute com `SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk`
para usar o SDK compatível com o linker instalado.

O engine reconhece `freedoom1.wad` como Doom/retail (episódios) e
`freedoom2.wad` como Doom II/commercial (MAPxx). A cópia mantém o engine da
base: DEHACKED está desativado e não foi acrescentado suporte a Boom.
O usuário confirmou o funcionamento das duas fases. A serial confirmou os
dois arquivos reconhecidos e a execução de Phase 1, com gráficos e SFX ativos,
sem abort/panic no trecho capturado. Após a inicialização, esse trecho registrou
25.9–41.5 FPS. O WAD foi lido por streaming do microSD porque não havia um
bloco contínuo de PSRAM disponível para armazená-lo inteiro.
Log: `.debug_logs/freedoom-invalid-wad-reboot.log`.
Essa validação não equivale a completar todos os mapas ou testar cada recurso.

Se o menu mostrar "AUSENTE OU INVALIDO", confirme o caminho, extraia o ZIP,
pressione R e confira a serial: ela distingue falha ao abrir o arquivo de
cabeçalho IWAD inválido. O firmware precisa incluir `CONFIG_FATFS_LFN_HEAP=y`;
a configuração antiga 8.3 não permite abrir `freedoom1.wad`/`freedoom2.wad`.

O menu e a transição de iluminação foram validados no projeto Final Doom.
Seu histórico está em `TAB5FINALDOOM_BASE_HISTORY.txt`; o progresso desta
versão está em `TAB5DOOM_PROGRESS.txt`.

## Licença e créditos

Engine doomgeneric: GPL-2.0-or-later, id Software, Simon Howard e colaboradores,
ozkl e Alejandro Villegas Alonso (ESP32P4DOOM). Drivers e teclado mantêm seus
avisos em main/THIRD_PARTY_NOTICES.txt. Os dados Freedoom mantêm a licença
original em `downloads/freedoom-0.13.0/COPYING.txt`.
