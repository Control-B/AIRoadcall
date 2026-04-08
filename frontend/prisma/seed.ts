import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  console.log("Seeding database...");

  // Create mechanics
  const mechanic1 = await prisma.mechanic.upsert({
    where: { phone: "+15551234001" },
    update: {},
    create: {
      companyName: "QuickFix Auto Services",
      contactName: "Mike Johnson",
      phone: "+15551234001",
      serviceTypes: ["flat_tire", "dead_battery", "lockout", "fuel_delivery", "tow_needed"],
      vehicleTypesSupported: ["sedan", "suv", "truck", "van"],
      baseLat: 34.0522,
      baseLng: -118.2437,
      active: true,
      acceptsMobileRoadside: true,
      rating: 4.8,
      lastKnownLat: 34.0480,
      lastKnownLng: -118.2500,
      lastLocationUpdatedAt: new Date(),
    },
  });

  const mechanic2 = await prisma.mechanic.upsert({
    where: { phone: "+15551234002" },
    update: {},
    create: {
      companyName: "Roadside Rescue Pro",
      contactName: "Sarah Williams",
      phone: "+15551234002",
      serviceTypes: ["flat_tire", "dead_battery", "engine_trouble", "overheating", "tow_needed"],
      vehicleTypesSupported: ["sedan", "suv", "truck"],
      baseLat: 34.0195,
      baseLng: -118.4912,
      active: true,
      acceptsMobileRoadside: true,
      rating: 4.5,
    },
  });

  const mechanic3 = await prisma.mechanic.upsert({
    where: { phone: "+15551234003" },
    update: {},
    create: {
      companyName: "24/7 Mobile Mechanics",
      contactName: "David Chen",
      phone: "+15551234003",
      serviceTypes: ["dead_battery", "lockout", "fuel_delivery", "engine_trouble"],
      vehicleTypesSupported: ["sedan", "suv", "van", "motorcycle"],
      baseLat: 34.0736,
      baseLng: -118.4004,
      active: true,
      acceptsMobileRoadside: true,
      rating: 4.2,
    },
  });

  // Create sample job (awaiting driver location)
  const job1 = await prisma.job.upsert({
    where: { publicJobId: "RC-SEED0001" },
    update: {},
    create: {
      publicJobId: "RC-SEED0001",
      magicLinkToken: "seed-token-awaiting-location",
      magicLinkExpiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
      driverName: "Alex Rivera",
      driverPhone: "+15559876543",
      vehicleType: "sedan",
      issueType: "flat_tire",
      issueSummary:
        "Front passenger tire is completely flat. Driver is on the shoulder of I-405 northbound near exit 52.",
      status: "awaiting_driver_location",
      paymentStatus: "not_started",
      paymentHoldAmount: 150.0,
    },
  });

  // Create sample job (mechanic en route for tracking test)
  const job2 = await prisma.job.upsert({
    where: { publicJobId: "RC-SEED0002" },
    update: {},
    create: {
      publicJobId: "RC-SEED0002",
      magicLinkToken: "seed-token-tracking-test",
      magicLinkExpiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
      driverName: "Jordan Smith",
      driverPhone: "+15559876544",
      vehicleType: "suv",
      issueType: "dead_battery",
      issueSummary:
        "Car won't start. Battery appears dead. Parked at a gas station on Wilshire Blvd.",
      status: "mechanic_en_route",
      paymentStatus: "authorized",
      paymentHoldAmount: 175.0,
      driverLat: 34.0622,
      driverLng: -118.2337,
      driverLocationCapturedAt: new Date(),
      assignedMechanicId: mechanic1.id,
    },
  });

  // Dispatch attempt for job2
  await prisma.mechanicDispatchAttempt.create({
    data: {
      jobId: job2.id,
      mechanicId: mechanic1.id,
      rankScore: 0.92,
      dispatchStatus: "accepted",
      calledAt: new Date(Date.now() - 10 * 60 * 1000),
      respondedAt: new Date(Date.now() - 8 * 60 * 1000),
      availabilityEtaMinutes: 15,
      notes: "On my way, about 15 minutes out.",
    },
  });

  // Tracking session for job2
  await prisma.trackingSession.create({
    data: {
      jobId: job2.id,
      mechanicId: mechanic1.id,
      trackingStatus: "active",
      startedAt: new Date(Date.now() - 7 * 60 * 1000),
    },
  });

  console.log("Seed complete!");
  console.log(`\nJob 1 (awaiting location): ${job1.publicJobId}`);
  console.log(`  Token: ${job1.magicLinkToken}`);
  console.log(`\nJob 2 (tracking test): ${job2.publicJobId}`);
  console.log(`  Token: ${job2.magicLinkToken}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
