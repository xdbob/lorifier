#!/usr/bin/env python3

# Utility script to modify the display of email in mutt.
#
# Installation:
#   In muttrc, set the following:
#     set display_filter="$HOME/.mutt/lorifier.py"
#     ignore *
#     unignore from date subject to cc x-date x-uri message-id
#
# Note that it's important that message-id is unignored; only unignored headers
# are passed to display_filter. If message-id is not passed, x-uri won't be
# generated. Therefore as a workaround, the message-id header will be removed
# so that it will not actually be displayed.
#
# This script contains the following functions:
#   X-Date: Add an X-Date header, which is Date translated to localtime
#   X-URI: Add an X-URI header, which is added when lore-compatible mail is
#          found

import email
import email.policy
import os
import sys
import time

from email.utils import mktime_tz, parsedate_tz, formatdate

LORE_FMT = "https://lore.kernel.org/{}/{}/"
LORE_MLS = {
    "qemu-devel@nongnu.org": "qemu-devel",
}

class muttemail:
    in_policy = email.policy.default
    print_policy = email.policy.HTTP.clone(linesep=os.linesep)

    def __init__(self, raw_message):
        self.message = email.message_from_bytes(
            raw_message,
            policy=self.in_policy,
        )

    def as_string(self):
        return self.message.as_string(policy=self.print_policy)

    def as_bytes(self):
        return self.message.as_bytes(policy=self.print_policy)

    def create_xdate_header(self):
        """ Add an X-Date header, which is Date converted to localtime. """
        date = self.message.get("Date", None)
        if not date:
            return

        try:
            tz_tuple = parsedate_tz(date)
            epoch_time = mktime_tz(tz_tuple)
            self.message.add_header("X-Date", formatdate(epoch_time, localtime=True))
        except Exception as e:
            self.message.add_header("X-Date", f'Error: {e}')


    def remove_header(self, header):
        """ Remove the named header """
        for i in reversed(range(len(self.message._headers))):
            header_name = self.message._headers[i][0].lower()
            if header_name == header.lower():
                del (self.message._headers[i])

    def create_xuri_header(self):
        """
        If the mail is sent to a lore-supported mailing list, provide a header
        with a lore link directly.

        Message-ID header must be present. Be sure it is unignored. Use
        remove_header("Message-ID") to avoid displaying Message-ID.
        """

        message_id = self.message.get("Message-ID", None)
        if not message_id:
            return

        recipients_headers = self.message.get_all("To", [])
        recipients_headers.extend(self.message.get_all("Cc", []))
        recipients = [addr for _name, addr in email.utils.getaddresses(recipients_headers)]

        for recipient in recipients:
            mailing_list = LORE_MLS.get(recipient)
            if mailing_list is None and recipient.endswith("@vger.kernel.org"):
                mailing_list = recipient[:-len("@vger.kernel.org")]

            if mailing_list:
                self.message.add_header(
                    "X-URI",
                    LORE_FMT.format(mailing_list, message_id[1:-1])
                )


if __name__ == "__main__":
    e = muttemail(sys.stdin.buffer.read())
    e.create_xdate_header()
    e.create_xuri_header()
    #e.remove_header("Message-ID")
    sys.stdout.buffer.write(e.as_bytes())
    #sys.stdout.write(e.as_string())
