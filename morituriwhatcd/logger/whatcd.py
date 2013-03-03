# -*- Mode: Python; test-case-name: morituriwhatcd.test.test_logger_whatcd -*-

import os
import time
import hashlib

from morituri.common import common
from morituri.configure import configure
from morituri.result import result


class WhatCDLogger(result.Logger):

    _accuratelyRipped = 0
    _inARDatabase = 0
    _errors = False

    def _framesToMSF(self, frames):
        # format specifically for EAC log; examples:
        # 5:39.57
        f = frames % common.FRAMES_PER_SECOND
        frames -= f
        s = (frames / common.FRAMES_PER_SECOND) % 60
        frames -= s * 60
        m = frames / common.FRAMES_PER_SECOND / 60

        return "%2d:%02d.%02d" % (m, s, f)

    def _framesToHMSH(self, frames):
        # format specifically for EAC log; examples:
        # 0:00.00.70
        # FIXME: probably depends on General EAC setting (display as frames)
        # if this formats as frames or as hundreds of seconds
        f = frames % common.FRAMES_PER_SECOND
        frames -= f
        s = (frames / common.FRAMES_PER_SECOND) % 60
        frames -= s * 60
        m = frames / common.FRAMES_PER_SECOND / 60
        frames -= m * 60
        h = frames / common.FRAMES_PER_SECOND / 60 / 60

        #return "%2d:%02d:%02d.%02d" % (h, m, s, int((f / 75.0) * 100.0))
        return "%2d:%02d:%02d.%02d" % (h, m, s, f)


    def log(self, ripResult, epoch=time.time()):
        lines = self.logRip(ripResult, epoch=epoch)
        return '\n'.join(lines)


    def logRip(self, ripResult, epoch):

        lines = []

        ### global

        # version string; FIXME
        lines.append("morituri version %s" % configure.version)
        lines.append("")

        # date when EAC writes the log file
        # using %e for day of month and strip because EAC formats like this:
        # 4. June 2009, 16:18
        # 6. September 2009, 9:14
        # %-H formats the hour with one digit only when it's one digit
        date = time.strftime("%e. %B %Y, %-H:%M", time.localtime(epoch)).strip()
        lines.append("morituri extraction logfile from %s" % date)
        lines.append("")

        # album
        lines.append("%s / %s" % (ripResult.artist, ripResult.title))
        lines.append("")

        # drive
        lines.append(
            "Used drive  : %s%s %s" % (
                ripResult.vendor, ripResult.model, ripResult.release))
        lines.append("")

        # Default for cdparanoia; every sector gets read at least twice
        lines.append("Read mode                : Secure")
        lines.append("Use cdparanoia mode      : Yes (cdparanoia %s)" % (
            ripResult.cdparanoiaVersion))
        defeat = 'Unknown'
        if ripResult.cdparanoiaDefeatsCache is True:
            defeat = 'Yes'
        if ripResult.cdparanoiaDefeatsCache is False:
            defeat = 'No'
        lines.append("Defeat audio cache       : %s" % defeat)
        # Default for cdparanoia by virtue of having no C2 rip mode
        lines.append("Make use of C2 pointers  : No")

        lines.append("")

        lines.append("Read offset correction                      : %d" %
            ripResult.offset)
        # Currently unsupported by cdparanoia
        lines.append("Overread into Lead-In and Lead-Out          : No")
        # Default for cdparanoia
        lines.append("Fill up missing offset samples with silence : Yes")
        # Default for cdparanoia
        lines.append("Delete leading and trailing silent blocks   : No")
        # Default
        lines.append("Null samples used in CRC calculations       : Yes")
        lines.append("Gap Detection                               : "
            "cdrdao version %s" % ripResult.cdrdaoVersion)
        lines.append("Gap handling                                : "
            "Appended to previous track")
        lines.append("")
        lines.append("Used output format              : %s" %
            ripResult.profileName)
        lines.append("GStreamer pipeline              : %s" %
            ripResult.profilePipeline)
        lines.append("GStreamer version               : %s" %
            ripResult.gstreamerVersion)
        lines.append("GStreamer Python version        : %s" %
            ripResult.gstPythonVersion)
        lines.append("Encoder plugin version          : %s" %
            ripResult.encoderVersion)
        lines.append("")
        lines.append("")

        # toc
        lines.append("TOC of the extracted CD")
        lines.append("")
        lines.append(
            "     Track |   Start  |  Length  | Start sector | End sector ")
        lines.append(
            "    ---------------------------------------------------------")
        table = ripResult.table


        for t in table.tracks:
            # FIXME: what happens to a track start over 60 minutes ?
            start = t.getIndex(1).absolute
            length = table.getTrackLength(t.number)
            end = table.getTrackEnd(t.number)
            lines.append(
            "       %2d  | %s | %s |    %6d    |   %6d   " % (
                t.number, 
                self._framesToMSF(start),
                self._framesToMSF(length),
                start, end))

        lines.append("")
        lines.append("")

        ### per-track
        duration = 0.0
        for t in ripResult.tracks:
            lines.extend(self.trackLog(t))
            lines.append('')
            duration += t.testduration + t.copyduration

        ### global overview
        # FIXME

        lines.append("")
        lines.append("Wall clock time to rip all tracks: %.3f minutes" % (
            duration / 60.0))
        lines.append("")
        if self._inARDatabase == 0:
            lines.append("None of the tracks are present "
                         "in the AccurateRip database")
        else:
            nonHTOA = len(ripResult.tracks)
            if ripResult.tracks[0].number == 0:
                nonHTOA -= 1
            if self._accuratelyRipped < nonHTOA:
                lines.append("%d track(s) accurately ripped" %
                    self._accuratelyRipped)
                lines.append("")
                lines.append("Some tracks could not be verified as accurate")
                self._errors = True
            else:
                lines.append("All tracks accurately ripped")

        lines.append("")
        if self._errors:
            lines.append("There were errors")
        else:
            lines.append("No errors occurred")
        lines.append("")
        lines.append("End of status report")
        lines.append("")

        hasher = hashlib.sha256()
        hasher.update("\n".join(lines).encode("utf-8"))
        lines.append("==== Log Checksum: %s ====" % hasher.hexdigest())
        lines.append("")

        return lines

    def trackLog(self, trackResult):

        lines = []

        lines.append('Track %2d' % trackResult.number)
        lines.append('')
        lines.append('     Filename %s' % trackResult.filename)
        lines.append('')

        # EAC adds the 2 seconds to the first track pregap
        pregap = trackResult.pregap
        if trackResult.number == 1:
            pregap += 2 * common.FRAMES_PER_SECOND
        if pregap:
            lines.append('     Pre-gap length %s' % self._framesToHMSH(
                pregap))
            lines.append('')

        # EAC seems to format peak differently, truncating to the 3rd digit,
        # and also calculating it against a max of 32767
        # MBV - Feed me with your kiss: replaygain 0.809875,
        # EAC's peak level 80.9 % instead of 90.0 %
        peak = trackResult.peak * 32768 / 32767
        #lines.append('     Peak level %r' % peak)
        lines.append('     Peak level %.1f %%' % (
            int(peak * 1000) / 10.0))
        #level = "%.2f" % (trackResult.peak * 100.0)
        #level = level[:-1]
        #lines.append('     Peak level %s %%' % level)
        # Track quality is shown in secure mode
        if trackResult.quality and trackResult.quality > 0.001:
            lines.append('     Track quality %.1f %%' % (
                trackResult.quality * 100.0, ))
        if trackResult.testspeed:
            lines.append('     Extraction Speed (Test) %.4f X' % (
                trackResult.testspeed))
        if trackResult.copyspeed:
            lines.append('     Extraction Speed (Copy) %.4f X' % (
                trackResult.copyspeed))
        if trackResult.testcrc is not None:
            lines.append('     Test CRC %08X' % trackResult.testcrc)
        if trackResult.copycrc is not None:
            lines.append('     Copy CRC %08X' % trackResult.copycrc)
        
        if trackResult.accurip:
            self._inARDatabase += 1
            if trackResult.ARCRC == trackResult.ARDBCRC:
                lines.append('     Accurately ripped (confidence %d)  [%08X]' % (
                    trackResult.ARDBConfidence, trackResult.ARCRC))
                self._accuratelyRipped += 1
            else:
                lines.append('     Cannot be verified as accurate  '
                    '(confidence %d),  [%08X], AccurateRip returned [%08x]' % (
                        trackResult.ARDBConfidence,
                        trackResult.ARCRC, trackResult.ARDBCRC))
        else:
            lines.append('     Track not present in AccurateRip database')

        if trackResult.testcrc == trackResult.copycrc:
            lines.append('     Copy OK')
        # FIXME: else ?
        return lines

