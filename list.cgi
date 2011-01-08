#!/usr/bin/perl
use strict;
binmode STDOUT, q(:utf8);
use CGI::Carp qw(fatalsToBrowser);

my $Timeout = 1;
my $HostsInfoFileName = q[hosts.dat];
my $LockFileName = q[.lock];

sub htescape ($) {
  my $s = shift;
  $s =~ s/&/&amp;/g;
  $s =~ s/</&lt;/g;
  $s =~ s/>/&gt;/g;
  $s =~ s/"/&quot;/g;
  return $s;
} # htescape

sub print_sheets () {
  print q[
<style>
  table {
    width: 90%;
  }

  input {
    width: 100%;
  }

  td {
    text-align: center;
  }
<style>
.error {
  background-color: red;
  color: black;
}
.comment {
  color: green;
  background-color: transparent;
}

.alive {
  background-color: green;
  color: white;
}
.dead {
  background-color: red;
  color: black;
}

.registered {

}
.not-registered {
  background-color: #C0C0C0;
  color: black;
}

th, td {
  padding-right: 1em;
}
</style>
<script>
  function ping (node, addr) {
    node.textContent = '...';
    node.className = '';
    var req = new XMLHttpRequest (addr);
    req.open ("GET", "ping/" + addr, true);
    req.onreadystatechange = function () {
      if (req.readyState == 4) {
        if (req.status < 400) {
	  node.textContent = req.responseText;
          if (req.responseText == 'dead') {
            node.className = 'dead';
          } else {
	    node.className = 'alive';
          }
        } else {
          node.textContent = 'FAIL (' + req.status + ')';
        }
      }
    };
    req.send (null);
  }
</script>];
} # print_sheets

sub get_hosts_info () {
  my $hosts_info = {};
  open my $hosts_info_file, '<:utf8', $HostsInfoFileName or die "$0: $HostsInfoFileName: $!";
  while (<$hosts_info_file>) {
    tr/\x0D\x0A//d;
    my @data = split /\t/, $_;
    my $addr = shift @data;
    $hosts_info->{$addr} = \@data;
  }
  return $hosts_info;
} # get_hosts_info

sub set_hosts_info ($) {
  my $hosts_info = shift;
  open my $hosts_info_file, '>:utf8', $HostsInfoFileName or die "$0: $HostsInfoFileName: $!";
  print $hosts_info_file
    join "\n", map {
      join ("\t", $_, map {tr/\x0D\x0A\x09/   /; $_} @{$hosts_info->{$_}})
    } sort {$a cmp $b} grep { $hosts_info->{$_} } keys %$hosts_info;
} # set_hosts_info

{
  my $lock_file;
  sub lock_hosts_info () {
    use Fcntl qw(LOCK_EX);
    open my $lock_file, '>', $LockFileName or die "$0: $LockFileName: $!";
    flock $lock_file, LOCK_EX;
  } # lock_hosts_info
}

sub commit_version (;$) {
  system 'svn', 'commit', '-m', $_[0] || 'updated', 'hosts.dat';
} # commit_version

{
  my $ping;
  sub ping ($$) {
    require Net::Ping;
    $ping ||= Net::Ping->new ('external');
    $ping->hires;
    return $ping->ping (@_);
  } # ping
}

my $path = $ENV{PATH_INFO};
if ($path =~ m#/ping/([^/]+)#) {
  my $addr = $1;
  print "Content-Type: text/plain; charset=us-ascii\nCache-Control: no-cache\n\n";
  my ($ret, $duration) = ping ($addr, $Timeout);
  if ($ret) {
    printf "alive (%.2f [ms])", $duration * 1000;
  } else {
    print "dead";
  }
  exit;
} elsif ($path eq '/all' or $path eq '/all+ping' or
	 $path eq '/all+ping-static') {
  print "Content-Type: text/html; charset=utf-8\n\n";
  $| = 1;
  my $ping = 1 if $path eq '/all+ping';
  $ping = 2 if $path eq '/all+ping-static';

print q[<!DOCTYPE HTML><html lang=en><head>
    <base href="/imase-lab/network/addr/list/">
	<title>Status of Network Hosts</title>];
  print_sheets ();
  print q[<body>
<nav>[<a href="all">List w/o ping</a> <a href="all+ping">List w/ping (Ajax)</a>
<a href="all+ping-static">List w/ping</a> <a href="hosts">hosts</a>
<a href="../snapshot/latest" type="application/atom+xml" rel=feed>Daily
Snapshot (Atom feed)</a>]</nav>

<h1>Status of Network Hosts</h1>

<p>Date: ].(scalar gmtime).q[</p>

<p>Timeout: ].$Timeout.q[ [s]</p>
			  ];

  my $hosts_info = get_hosts_info ();

print q[<h2><code>imase-global</code> 
(<code>133.1.244.0/26</code>)</h2>];
print_thead ($ping);
for my $addr4 (0..63) {
  print_row ('133.1.244.'.$addr4, $hosts_info, $ping);
}
print q[</table>];

print q[<h2><code>imase-local</code> 
(<code>192.168.10.0/24</code>)</h2>];
print_thead ($ping);
for my $addr4 (0..255) {
  print_row ('192.168.10.'.$addr4, $hosts_info, $ping);
}
print q[</table>];

print q[<h2>Others</h2>];
print_thead ($ping);

for my $addr4 (sort {$a cmp $b} keys %$hosts_info) {
  print_row ($addr4, $hosts_info, $ping);
}

print q[</table>];

sub print_thead ($) {
  my $ping = shift;
  print q[<table><thead>
<tr><th scope=col>IP Address
<th scope=col>Host name(s)
<th scope=col>Owner
<th scope=col>Date of Registeration
	  <th scope=col>Description
<th scope=col>Location];
  print q[<th scope=col>Ping] if $ping;
  print q[<tbody>];
} # print_thead

sub print_row ($$$) {
  my $addr = shift;
  my $hosts_info = shift;
  my $ping = shift;
  my $eaddr = htescape ($addr);

  print qq[<tr><th scope=row><a href="entry/$eaddr"><code>$eaddr</code></a>];

  ## New hosts.dat
  my $entry = $hosts_info->{$addr};
  if ($entry->[0] or $entry->[1] or $entry->[2] or $entry->[3] or $entry->[4]) {
    my $class = $entry->[3] =~ /reserved|unused/ ? 'not-registered' : 'registered';
    print "<td class=$class>", htescape ($entry->[$_]) for 0..4;
  } else {
    print "<td colspan=5 class=not-registered>(not registered)";
  }

  if ($ping == 2) {
    my ($ret, $duration) = ping ($addr, $Timeout);
    if ($ret) {
      printf qq[<td class=alive>alive (%.2f [ms])], $duration * 1000;
    } else {
      print qq[<td class=dead>dead];
    }
  } elsif ($ping) {
    print qq[<td class=FAIL id="ping-$eaddr">FAIL (noscript)<script>
    ping (document.getElementById ("ping-$eaddr"), "$eaddr");
	     </script></td>];
  }
  delete $hosts_info->{$addr};
} # print_row

} elsif ($path =~ m#^/entry/([^/]+)$#) {
  my $addr = $1;
  if ($ENV{REQUEST_METHOD} eq 'POST') {
    lock_hosts_info ();
    my $hosts_info = get_hosts_info ();
    read STDIN, my $data, $ENV{CONTENT_LENGTH};
    require Encode;
    my $param;
    for (map {
           [map {s/\+/ /g; s/%([0-9A-Fa-f]{2})/pack 'C', hex $1/ge; Encode::decode ('utf-8', $_)}
	    split /=/, $_, 2]}
	 split /&/, $data) {
      $param->{$_->[0]} = $_->[1];
    }

    $hosts_info->{$addr} = [$param->{host}, $param->{owner}, $param->{'registration-date'}, $param->{description}, $param->{location}];
    set_hosts_info ($hosts_info);

    print "Status: 303 See Other\nLocation: $ENV{REQUEST_URI}\nContent-Type: text/html; charset=utf-8\n\n";
    commit_version ($addr . ' updated');
  } else {
    my $eaddr = htescape ($addr);
    my $hosts_info = get_hosts_info ();
    my $entry = $hosts_info->{$addr};
    my $has_entry = ($entry->[0] or $entry->[1] or $entry->[2] or $entry->[3] or $entry->[4]) ? 1 : 0;
    print "Content-Type: text/html; charset=utf-8\n\n";
    print qq[<!DOCTYPE HTML><html lang=en>
	     <title>Edit $eaddr</title>];
    print_sheets ();
    print qq[<h1>Edit <code>$eaddr</code></h1>
<form action="" method=post accept-charset=utf-8>
<table>
<tbody>
<tr><th scope=row>IP address<td><input value="$eaddr" readonly>
<tr title="Space-separated host names, possibly empty"><th scope=row>Host name(s)<td><input name=host value="@{[htescape ($entry->[0])]}">
<tr><th scope=row>Owner<td><input name=owner value="@{[htescape ($entry->[1])]}">
<tr><th scope=row>Date of registration<td><input type=date name=registration-date value="@{[$has_entry ? htescape ($entry->[2]) : (sprintf '%04d-%02d-%02d', (localtime)[5]+1900, (localtime)[4]+1, (localtime)[3])]}">
<tr><th scope=row>Description<td><input name=description value="@{[htescape ($entry->[3])]}">
<tr><th scope=row>Location<td><input name=location value="@{[htescape ($entry->[4])]}">
<tr><th scope=row>Ping<td class=FAIL id="ping-$eaddr">FAIL (noscript)<script>
  ping (document.getElementById ("ping-$eaddr"), "$eaddr");
</script>
<tr><td colspan=2><button type=submit>Update</button>
</table></form>];
  }
} elsif ($path eq '') {
  print qq[Content-Type: text/html; charset=us-ascii\n\n<!DOCTYPE HTML><html lang=en><title>Index</title><h1>Index</h1><ul>
  <li><a href=..>..</a>
  <li><a href=list/>list/</a></ul>];
} elsif ($path eq '/') {
  print qq[Content-Type: text/html; charset=us-ascii\n\n<!DOCTYPE HTML><html lang=en><title>Index of list/</title><h1>Index of list/</h1><ul>
  <li><a href=..>..</a>
  <li><a href=all>all</a>
  <li><a href="all+ping">all+ping</a>
  <li><a href="hosts">hosts</a></ul>];
} elsif ($path eq '/hosts') {
  print "Content-Type: text/plain; charset=utf-8\n\n";
  my $hosts_info = get_hosts_info ();
  for my $addr (sort {$a cmp $b} grep {$hosts_info->{$_}->[0]}
		keys %$hosts_info) {
    print "$addr\t$hosts_info->{$addr}->[0]\n";
  }
} else {
  print "Status: 404 Not Found\nContent-Type: text/plain; charset=us-ascii\n\n404";
}
