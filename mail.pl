#!/usr/bin/perl
use strict;

my $snapshot_dir_name = q</var/www/html/imase-lab/network/addr/snapshot/>;
my $ping_result_file_name = q</tmp/ping-result.html>;
my $ping_uri = q<https://kureha/imase-lab/network/addr/list/all+ping-static>;

system 'wget',
  '--no-check-certificate',
  -O => $ping_result_file_name,
  $ping_uri;

if (-f $ping_result_file_name) {
  my @time = gmtime;
  my $yt = sprintf '%04d%02d', $time[5] + 1900, $time[4] + 1;
  my $this_snapshot_dir_name = $snapshot_dir_name . $yt . '/';
  unless (-d $this_snapshot_dir_name) {
    chdir $snapshot_dir_name;
    mkdir $yt;
    system 'svn', 'add', $yt;
  }

  chdir $this_snapshot_dir_name;
  my $this_snapshot_file_name_base = sprintf '%02d', $time[3];
  my $this_snapshot_file_name = $this_snapshot_file_name_base . '.html';
  system 'cp', $ping_result_file_name => $this_snapshot_file_name;

  chdir $snapshot_dir_name;
  my $feed_file_name = 'latest.atom';
  {
    my $time_full = sprintf '%04d-%02d-%02dT%02d:%02d:%02dZ',
        $time[5] + 1900, $time[4] + 1, $time[3], $time[2], $time[1], $time[0];

    open my $feed_file, '>', $feed_file_name or die "$0: $feed_file_name: $!";
    print $feed_file qq[
    <feed xmlns="http://www.w3.org/2005/Atom">
      <id>https://kureha/imase-lab/network/addr/snapshot/latest</id>
      <title xml:lang="en">Status of Network Hosts</title>
      <updated>$time_full</updated>
      <author>
        <name></name>
      </author>
      <link rel="alternate" href="" type="application/octet-stream"/>
        <!-- An |alternate| is necessary for Thunderbird -->
      <link rel="self" href="https://kureha/imase-lab/network/addr/snapshot/latest"/>
      <entry>
        <id>https://kureha/imase-lab/network/addr/snapshot/$yt/$this_snapshot_file_name_base</id>
        <title>[$time_full] Status of Network Hosts</title>
        <published>$time_full</published>
        <updated>$time_full</updated>
        <summary type="html">&lt;a href="https://kureha/imase-lab/network/addr/snapshot/$yt/$this_snapshot_file_name_base">Status of Network Hosts as of $time_full&lt;/a></summary>
        <content type="text/html" src="https://kureha/imase-lab/network/addr/snapshot/$yt/$this_snapshot_file_name_base"/>
        <link rel="self" href="https://kureha/imase-lab/network/addr/snapshot/$yt/$this_snapshot_file_name_base"/>
        <link rel="alternate" type="text/html" href="https://kureha/imase-lab/network/addr/snapshot/$yt/$this_snapshot_file_name_base"/>
      </entry>
    </feed>];
  }

  system 'svn', 'commit', -m => 'auto-snapshot';
}
