# src/dartr_tools/r/runner.R  — fixed-dispatch dartRverse runner (no eval)
suppressWarnings(suppressMessages({
  library(jsonlite); library(dartRverse)
}))
suppressWarnings(suppressMessages(library(dartR.captive)))
args <- commandArgs(trailingOnly = TRUE)
req  <- jsonlite::fromJSON(args[[1]], simplifyVector = TRUE)
fn   <- req$fn
p    <- req$params
outdir <- req$workdir

# dartRverse internals (gl.compliance.check, utils.recalc.maf, gl.recalc.metrics, ...)
# write progress text to stdout via cat()/print() even when verbose = 0 is passed.
# Divert stdout to a throwaway sink for the duration of the call so that only the
# final JSON (emitted after sink() is lifted) reaches the parent process's stdout.
.rbridge_sink_path <- tempfile("rbridge-sink-")
.rbridge_sink <- file(.rbridge_sink_path, open = "wt")
sink(.rbridge_sink)

emit <- function(outputs) {
  sink()                 # restore real stdout (chatter no longer matters — see below)
  close(.rbridge_sink)
  unlink(.rbridge_sink_path)  # the sink is a throwaway diversion; don't let it accumulate on disk
  # I() (AsIs) forces `outputs` to serialize as a JSON array even when it has
  # length 1 — plain auto_unbox = TRUE would otherwise collapse a single-output
  # branch (e.g. gl.read.vcf) down to a bare JSON string instead of ["gl.rds"].
  # Written to a response FILE, not stdout: some wrapped calls (gl.LDNe) shell
  # out to a child process (NeEstimator/Ne2-1M) that writes progress text to
  # the runner's own fd 1. R's sink() above only redirects R-level output, not
  # a child process's inherited stdout fd, so that chatter would otherwise land
  # on stdout and corrupt JSON parsed from there. The response file sidesteps
  # this entirely — the caller (rbridge.call_gl) reads it instead of stdout.
  writeLines(jsonlite::toJSON(list(outputs = I(outputs)), auto_unbox = TRUE),
             file.path(outdir, "_rresp.json"))
}

if (fn == "gl.read.vcf") {
  gl <- if (!is.null(p$metafile)) gl.read.vcf(p$vcf, ind.metafile = p$metafile, verbose = 0) else gl.read.vcf(p$vcf, verbose = 0)
  out <- file.path(outdir, p$out); saveRDS(gl, out); emit(c(p$out))

} else if (fn == "gl.filter") {                       # generic filter chain, fixed ops only
  gl <- readRDS(p$rds)
  if (!is.null(p$callrate)) gl <- gl.filter.callrate(gl, threshold = p$callrate, verbose = 0)
  if (!is.null(p$maf))      gl <- gl.filter.maf(gl, threshold = p$maf, verbose = 0)
  if (!is.null(p$rdepth))   gl <- gl.filter.rdepth(gl, lower = p$rdepth, verbose = 0)
  if (isTRUE(p$monomorphs)) gl <- gl.filter.monomorphs(gl, verbose = 0)
  out <- file.path(outdir, p$out); saveRDS(gl, out); emit(c(p$out))

} else if (fn == "gl2plink") {
  gl <- readRDS(p$rds); gl2plink(gl, outfile = p$out, outpath = outdir, verbose = 0)
  emit(c(paste0(p$out, ".ped"), paste0(p$out, ".map")))

} else if (fn == "gl2vcf") {
  gl <- readRDS(p$rds); gl2vcf(gl, outfile = p$out, outpath = outdir, plink.bin.path = p$plink_path, verbose = 0)
  emit(c(paste0(p$out, ".vcf")))

} else if (fn == "gl.report.heterozygosity") {
  gl <- readRDS(p$rds); res <- gl.report.heterozygosity(gl, verbose = 0)
  out <- file.path(outdir, p$out); write.csv(res, out, row.names = FALSE); emit(c(p$out))

} else if (fn == "gl.fst.pop") {
  gl <- readRDS(p$rds); res <- gl.fst.pop(gl, verbose = 0)
  out <- file.path(outdir, p$out); saveRDS(res, out); emit(c(p$out))

} else if (fn == "gl.pcoa") {
  gl <- readRDS(p$rds); pc <- gl.pcoa(gl, verbose = 0)
  co <- file.path(outdir, p$out_coords); saveRDS(pc, co)
  pl <- file.path(outdir, p$out_plot)
  ggplot2::ggsave(pl, gl.pcoa.plot(pc, gl, verbose = 0), width = 7, height = 6)
  emit(c(p$out_coords, p$out_plot))

} else if (fn == "gl.LDNe") {
  gl <- readRDS(p$rds)
  res <- gl.LDNe(gl, outfile = p$out, outpath = outdir, neest.path = p$neest_path, verbose = 0)
  out <- file.path(outdir, "ne.rds"); saveRDS(res, out); emit(c("ne.rds"))

} else if (fn == "gl.run.EMIBD9") {
  gl  <- readRDS(p$rds)
  res <- gl.run.EMIBD9(gl, emibd9.path = p$emibd9_path, plot.out = FALSE,
                       ISeed = p$iseed, Inbreed = isTRUE(p$inbreed), verbose = 0)
  out <- file.path(outdir, "relatedness.csv")
  write.csv(res$rel, out)
  emit(c("relatedness.csv"))

} else {
  stop(paste("function not allowed:", fn))
}
